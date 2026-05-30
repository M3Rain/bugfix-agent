"""Wires nodes into a LangGraph state machine and exposes run()."""
from __future__ import annotations
from langgraph.graph import StateGraph, START, END

from agent.state import AgentState, Step
from agent import nodes, tools as tool_mod


def _step_cap(state: AgentState) -> int:
    """Hard ceiling on total agent steps, so an agent that never calls
    run_tests still terminates (independent of the per-test attempt budget)."""
    return (state.get("max_attempts") or 6) * 4


def _route_after_act(state: AgentState) -> str:
    """Decide what to do after an Action executes.

    The key idea: this is a real ReAct episode. read_file / edit_file just feed
    the next Thought (loop back to `reason`). We only Reflect when an actual
    run_tests FAILED — that is a genuine failed attempt worth a verbal lesson.
    """
    result = state.get("test_result") or {}
    history = state.get("history") or []
    last_tool = state.get("last_tool", "")

    if result.get("passed"):
        return "persist"                      # success — done
    if last_tool == "finish":
        return "persist"                      # agent declared done
    if len(history) >= _step_cap(state):
        return "reflect_final"                # safety cap hit — wrap up

    if state.get("tested"):                   # a test ran (edit or run_tests) and failed
        if (state.get("attempt") or 1) >= (state.get("max_attempts") or 6):
            return "reflect_final"
        return "reflect_retry"

    # read_file / failed edit / parse_error: keep working in the same episode.
    return "reason"


def _after_reflect(state: AgentState) -> str:
    """After reflecting on a failed test: stop if out of budget, else retry."""
    history = state.get("history") or []
    if ((state.get("attempt") or 1) >= (state.get("max_attempts") or 6)
            or len(history) >= _step_cap(state)):
        return "persist"
    return "bump_attempt"


def _bump_attempt(state: AgentState) -> dict:
    return {"attempt": (state.get("attempt") or 1) + 1}


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("reason", nodes.reason)
    g.add_node("act", nodes.act)
    g.add_node("reflect", nodes.reflect)
    g.add_node("bump_attempt", _bump_attempt)
    g.add_node("persist", nodes.persist)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "reason")
    g.add_edge("reason", "act")
    g.add_conditional_edges(
        "act",
        _route_after_act,
        {
            "persist": "persist",       # tests passed, or agent finished, or cap
            "reason": "reason",         # mid-episode tool step — keep going
            "reflect_retry": "reflect", # failed test, budget remains
            "reflect_final": "reflect", # failed test, last attempt / cap
        },
    )
    g.add_conditional_edges("reflect", _after_reflect, {
        "persist": "persist",
        "bump_attempt": "bump_attempt",
    })
    g.add_edge("bump_attempt", "reason")
    g.add_edge("persist", END)
    return g.compile()


def run(bug_name: str, max_attempts: int = 6) -> AgentState:
    """Top-level entrypoint: prepare sandbox + run the graph."""
    tool_mod.prepare_sandbox(bug_name)
    # Run the suite once up front so the agent's first Thought sees the real
    # failure instead of reasoning blind.
    seed_result = tool_mod.run_tests(bug_name)
    graph = build_graph()
    initial: AgentState = {
        "bug_name": bug_name,
        "history": [],
        "attempt": 1,
        "max_attempts": max_attempts,
        "retrieved_reflections": [],
        "new_reflections": [],
        "test_result": seed_result,
        "status": "running",
    }
    # A ReAct episode can take many reason/act super-steps before a test runs.
    # The history step-cap (max_attempts * 4) guarantees termination; set the
    # LangGraph recursion limit comfortably above the worst-case super-step
    # count so it never trips before our own guards do.
    config = {"recursion_limit": max_attempts * 12 + 20}
    final = graph.invoke(initial, config=config)
    final["status"] = "success" if (final.get("test_result") or {}).get("passed") else "failed"
    return final