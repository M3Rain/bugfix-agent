"""LangGraph node functions. Each takes an AgentState and returns a partial
state update dict."""
from __future__ import annotations
import re
from typing import Optional

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
    store = store or ReflectionStore()
    code = tool_mod.read_file(str(tool_mod.sandbox_path(state["bug_name"]) / f"{state['bug_name']}.py"))
    query = f"{state['bug_name']}\n{code[:500]}"
    hits = store.search(query, k=3)
    return {"retrieved_reflections": hits, "new_reflections": []}


def reason(state: AgentState, chat=None) -> dict:
    chat = chat or get_chat()
    bug = state["bug_name"]
    code_path = tool_mod.sandbox_path(bug) / f"{bug}.py"
    code = tool_mod.read_file(str(code_path))
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
        return {}
    step = history[-1]
    bug = state["bug_name"]
    sb = tool_mod.sandbox_path(bug)

    try:
        call = parse_action(step.action)
    except ParseError as e:
        step.observation = f"ParseError: {e}. Re-emit a valid Action."
        return {"history": history}

    tool, args = call["tool"], call["args"]
    try:
        if tool == "read_file":
            content = tool_mod.read_file(str(sb / args["path"]))
            step.observation = content
        elif tool == "edit_file":
            tool_mod.edit_file(str(sb / args["path"]), args["old"], args["new"])
            step.observation = f"ok — edited {args['path']}"
        elif tool == "run_tests":
            result = tool_mod.run_tests(bug)
            step.observation = (
                f"{'PASS' if result['passed'] else 'FAIL'}\n{result['output']}"
            )
            return {"history": history, "test_result": result}
        elif tool == "finish":
            step.observation = "finish requested"
            # let the routing layer decide if tests actually pass
        else:
            step.observation = f"unknown tool: {tool}"
    except Exception as e:
        step.observation = f"{type(e).__name__}: {e}"
    return {"history": history}


def reflect(state: AgentState, chat=None) -> dict:
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
    store = store or ReflectionStore()
    bug = state["bug_name"]
    for i, r in enumerate(state.get("new_reflections") or []):
        store.add(bug_name=bug, reflection=r, attempt=i + 1)
    return {}