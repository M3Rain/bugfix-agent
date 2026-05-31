"""Streamlit UI for the bug-fixing agent."""
import json
from pathlib import Path

import streamlit as st

from agent.graph import build_graph
from agent import tools as tool_mod

st.set_page_config(page_title="ReAct + Reflexion Bug Fixer", layout="wide")
st.title("🐛 ReAct + Reflexion Bug Fixer")

# ── Sidebar controls ──
DATA_DIR = Path("data/quixbugs")
INDEX = json.loads((DATA_DIR / "index.json").read_text())

with st.sidebar:
    bug_name = st.selectbox("Bug", INDEX, index=INDEX.index("bitcount") if "bitcount" in INDEX else 0)
    max_attempts = st.slider("Max attempts", 1, 10, 6)
    run_btn = st.button("▶ Run agent", use_container_width=True, type="primary")
    st.markdown("---")
    st.caption("Model: qwen2.5-coder:7b via Ollama")

# ── Layout ──
trace_col, mem_col = st.columns([2, 1])
with trace_col:
    st.subheader("Live agent trace")
    trace_area = st.empty()
with mem_col:
    st.subheader("Retrieved memory")
    retrieved_area = st.empty()
    st.subheader("New reflections (this run)")
    new_refl_area = st.empty()

result_area = st.empty()

if run_btn:
    tool_mod.prepare_sandbox(bug_name)
    graph = build_graph()
    initial = {
        "bug_name": bug_name,
        "history": [],
        "attempt": 1,
        "max_attempts": max_attempts,
        "retrieved_reflections": [],
        "new_reflections": [],
        "test_result": {"passed": False, "output": "(not run yet)", "timed_out": False},
        "status": "running",
    }

    for event in graph.stream(initial, stream_mode="values"):
        # Update memory panels
        if event.get("retrieved_reflections"):
            retrieved_area.markdown(
                "\n".join(f"- {r}" for r in event["retrieved_reflections"]) or "_(none)_"
            )
        if event.get("new_reflections"):
            new_refl_area.markdown(
                "\n".join(f"- {r}" for r in event["new_reflections"]) or "_(none)_"
            )
        # Re-render the whole trace each event. A step is created by `reason`
        # with an empty observation and only filled in later by `act`, so we
        # must redraw — not append-once — or the observation stays blank.
        history = event.get("history") or []
        with trace_area.container():
            for i, s in enumerate(history, 1):
                st.markdown(f"**🧠 Thought ({i}):** {s.thought}")
                st.code(s.action, language="python")
                st.markdown("**👁 Observation:**")
                st.code(s.observation[:1500] or "(running…)", language="text")
                st.markdown("---")

    passed = event.get("test_result", {}).get("passed", False)
    if passed:
        result_area.success(f"✅ Fixed in {len(history)} step(s)")
    else:
        result_area.error(f"❌ Could not fix within {max_attempts} attempts")