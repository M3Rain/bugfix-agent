"""LangGraph node functions. Each takes an AgentState and returns a partial
state update dict."""
from __future__ import annotations
import os
import re
from typing import Optional


def _reflexion_disabled() -> bool:
    """Ablation switch: when set, the agent runs as pure ReAct — no retrieval,
    no verbal reflection, no long-term memory writes."""
    return os.environ.get("BUGFIX_DISABLE_REFLEXION") == "1"

from agent.state import AgentState, Step
from agent.prompts import SYSTEM_PROMPT, REASON_USER_PROMPT, REFLECT_PROMPT
from agent.parser import parse_action, ParseError
from agent import tools as tool_mod
from agent.llm import get_chat
from agent.memory import ReflectionStore


_THOUGHT_RE = re.compile(r"Thought:\s*(.+?)\nAction:\s*(.+)", re.DOTALL)


def _format_history(history: list[Step]) -> str:
    if not history:
        return "(no prior steps)"
    parts = []
    for i, s in enumerate(history, 1):
        parts.append(
            f"Step {i}\n"
            f"  Thought: {s.thought}\n"
            f"  Action: {s.action}\n"
            f"  Observation: {s.observation[:500]}"
        )
    return "\n".join(parts)


def retrieve(state: AgentState, store: Optional[ReflectionStore] = None) -> dict:
    if _reflexion_disabled():
        return {"retrieved_reflections": [], "new_reflections": []}
    store = store or ReflectionStore()
    code = tool_mod.read_file(str(tool_mod.program_path(state["bug_name"])))
    query = f"{state['bug_name']}\n{code[:500]}"
    hits = store.search(query, k=3)
    return {"retrieved_reflections": hits, "new_reflections": []}


def reason(state: AgentState, chat=None) -> dict:
    chat = chat or get_chat()
    bug = state["bug_name"]
    code = tool_mod.read_file(str(tool_mod.program_path(bug)))
    last_test = (state.get("test_result") or {}).get("output", "(not run yet)")

    sys = SYSTEM_PROMPT.format(
        retrieved_reflections="\n- " + "\n- ".join(state.get("retrieved_reflections") or ["(none)"]),
        new_reflections="\n- " + "\n- ".join(state.get("new_reflections") or ["(none)"]),
    )
    user = REASON_USER_PROMPT.format(
        bug_name=bug,
        attempt=state.get("attempt", 1),
        max_attempts=state.get("max_attempts", 6),
        buggy_code=code,
        last_test_output=last_test,
        history_text=_format_history(state.get("history") or []),
    )
    resp = chat.invoke([{"role": "system", "content": sys}, {"role": "user", "content": user}])
    text = resp.content

    m = _THOUGHT_RE.search(text)
    if m:
        thought, action = m.group(1).strip(), m.group(2).strip().splitlines()[0].strip()
    else:
        thought, action = "(no thought parsed)", text.strip().splitlines()[-1]

    new_step = Step(thought=thought, action=action, observation="")
    return {"history": (state.get("history") or []) + [new_step]}


def act(state: AgentState) -> dict:
    history = list(state.get("history") or [])
    if not history:
        return {"last_tool": "none", "tested": False}
    step = history[-1]
    bug = state["bug_name"]
    sb = tool_mod.sandbox_path(bug)

    try:
        call = parse_action(step.action)
    except ParseError as e:
        step.observation = f"ParseError: {e}. Re-emit a valid Action."
        return {"history": history, "last_tool": "parse_error", "tested": False}

    tool, args = call["tool"], call["args"]
    update = {"history": history, "last_tool": tool, "tested": False}
    try:
        if tool == "read_file":
            step.observation = tool_mod.read_file(str(sb / args["path"]))
        elif tool == "edit_file":
            # Guard 1: refuse edits that inject a print() the original didn't
            # have. A 7B model ignores the "no print()" prompt rule; the print
            # lands at the wrong indent, breaks import, and the agent spirals.
            if "print(" in args["new"] and "print(" not in args["old"]:
                step.observation = (
                    "Rejected: do not add print() statements — you cannot see "
                    "their output and they corrupt indentation. Fix the program "
                    "logic directly instead."
                )
                return update  # not tested → routing keeps the episode going
            # Guard 2: refuse an edit identical to one already tried this run.
            # The prompt says don't repeat, but the model re-emits byte-identical
            # edits; enforce it in code so it can't loop on a dead end.
            prior_edits = set()
            for past in history[:-1]:
                try:
                    pc = parse_action(past.action)
                except ParseError:
                    continue
                if pc["tool"] == "edit_file":
                    prior_edits.add((pc["args"].get("old"), pc["args"].get("new")))
            if (args["old"], args["new"]) in prior_edits:
                step.observation = (
                    "Rejected: you already tried this exact edit and it did not "
                    "work. Try a DIFFERENT change."
                )
                return update  # not tested → routing keeps the episode going
            tool_mod.edit_file(str(sb / args["path"]), args["old"], args["new"])
            # Auto-verify: a weak local model won't reliably choose to test, and
            # reasoning without test feedback just guesses. Running the suite
            # after every edit grounds the next Thought in a real result and
            # makes each edit count as one attempt.
            result = tool_mod.run_tests(bug)
            update["test_result"] = result
            update["tested"] = True
            verdict = "PASS" if result["passed"] else "FAIL"
            step.observation = (
                f"ok — edited {args['path']}\n"
                f"Tests after edit: {verdict}\n{result['output']}"
            )
        elif tool == "run_tests":
            result = tool_mod.run_tests(bug)
            update["test_result"] = result
            update["tested"] = True
            step.observation = (
                f"{'PASS' if result['passed'] else 'FAIL'}\n{result['output']}"
            )
        elif tool == "finish":
            step.observation = "finish requested"
            # routing layer decides whether tests actually pass
        else:
            step.observation = f"unknown tool: {tool}"
    except Exception as e:
        # e.g. EditError (ambiguous/missing old): not a test failure — let the
        # agent retry within the same episode rather than burning an attempt.
        step.observation = f"{type(e).__name__}: {e}"
    return update


def reflect(state: AgentState, chat=None) -> dict:
    if _reflexion_disabled():
        return {}                       # ablation: no verbal self-criticism
    chat = chat or get_chat(temperature=0.4)
    bug = state["bug_name"]
    attempt_history = _format_history(state.get("history") or [])
    test_output = (state.get("test_result") or {}).get("output", "")
    prompt = REFLECT_PROMPT.format(
        bug_name=bug,
        attempt_history=attempt_history,
        test_output=test_output,
    )
    resp = chat.invoke([{"role": "user", "content": prompt}])
    text = resp.content.strip()
    if not text.startswith("Lesson:"):
        text = "Lesson: " + text
    return {"new_reflections": (state.get("new_reflections") or []) + [text]}


def persist(state: AgentState, store: Optional[ReflectionStore] = None) -> dict:
    if _reflexion_disabled():
        return {}                       # ablation: nothing to save
    store = store or ReflectionStore()
    bug = state["bug_name"]
    for i, r in enumerate(state.get("new_reflections") or []):
        store.add(bug_name=bug, reflection=r, attempt=i + 1)
    return {}