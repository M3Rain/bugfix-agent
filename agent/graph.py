"""Wires nodes into a LangGraph state machine and exposes run()."""
from __future__ import annotations
from langgraph.graph import StateGraph, START, END

from agent.state import AgentState, Step
from agent import nodes, tools as tool_mod


def _should_continue(state: AgentState) -> str:
    """Routing after Observe."""
    result = state.get("test_result") or {}
    if result.get("passed"):
        return "persist"
    if (state.get("attempt") or 1) >= (state.get("max_attempts") or 6):
        return "reflect_final"
    return "reflect_then_retry"


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
        _should_continue,
        {
            "persist": "persist",                  # tests passed
            "reflect_then_retry": "reflect",       # tests failed, more attempts
            "reflect_final": "reflect",            # tests failed, last attempt
        },
    )
    # After reflect we either bump+reason or persist+END based on attempts
    def _after_reflect(state: AgentState) -> str:
        if (state.get("attempt") or 1) >= (state.get("max_attempts") or 6):
            return "persist"
        return "bump_attempt"

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
    graph = build_graph()
    initial: AgentState = {
        "bug_name": bug_name,
        "history": [],
        "attempt": 1,
        "max_attempts": max_attempts,
        "retrieved_reflections": [],
        "new_reflections": [],
        "test_result": {"passed": False, "output": "(not run yet)", "timed_out": False},
        "status": "running",
    }
    final = graph.invoke(initial)
    final["status"] = "success" if (final.get("test_result") or {}).get("passed") else "failed"
    return final