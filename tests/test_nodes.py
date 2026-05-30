from unittest.mock import MagicMock, patch
from agent.state import AgentState, Step
from agent import nodes


def test_retrieve_populates_reflections(tmp_path, monkeypatch):
    monkeypatch.setenv("BUGFIX_WORKDIR", str(tmp_path / "wd"))
    sb = tmp_path / "wd" / "bitcount"
    sb.mkdir(parents=True)
    (sb / "bitcount.py").write_text("def bitcount(n): return 0\n")

    fake_store = MagicMock()
    fake_store.search.return_value = ["Lesson: check base case"]
    state: AgentState = {"bug_name": "bitcount", "history": []}
    new = nodes.retrieve(state, store=fake_store)
    assert new["retrieved_reflections"] == ["Lesson: check base case"]


def test_act_executes_read_file(tmp_path, monkeypatch):
    monkeypatch.setenv("BUGFIX_WORKDIR", str(tmp_path / "wd"))
    sb = tmp_path / "wd" / "x"
    sb.mkdir(parents=True)
    (sb / "x.py").write_text("hello")
    state: AgentState = {
        "bug_name": "x",
        "history": [Step(thought="read it", action='read_file(path="x.py")', observation="")],
        "attempt": 1,
    }
    out = nodes.act(state)
    assert "hello" in out["history"][-1].observation


def test_act_handles_parse_error():
    state: AgentState = {
        "bug_name": "x",
        "history": [Step(thought="...", action="garbage not a call", observation="")],
        "attempt": 1,
    }
    out = nodes.act(state)
    assert "ParseError" in out["history"][-1].observation or "not a tool call" in out["history"][-1].observation



def test_reason_appends_step_with_mocked_llm(tmp_path, monkeypatch):
    monkeypatch.setenv("BUGFIX_WORKDIR", str(tmp_path / "wd"))
    sb = tmp_path / "wd" / "x"
    sb.mkdir(parents=True)
    (sb / "x.py").write_text("def x(): return 0\n")

    fake_chat = MagicMock()
    fake_chat.invoke.return_value = MagicMock(
        content='Thought: I will read the file.\nAction: read_file(path="x.py")'
    )
    state: AgentState = {
        "bug_name": "x",
        "history": [],
        "attempt": 1,
        "max_attempts": 6,
        "retrieved_reflections": [],
        "new_reflections": [],
        "test_result": {"passed": False, "output": "", "timed_out": False},
    }
    out = nodes.reason(state, chat=fake_chat)
    assert len(out["history"]) == 1
    assert out["history"][0].thought.startswith("I will read")
    assert 'read_file' in out["history"][0].action



def test_reflect_appends_reflection_with_mocked_llm():
    fake_chat = MagicMock()
    fake_chat.invoke.return_value = MagicMock(content="Lesson: check the base case.")
    state: AgentState = {
        "bug_name": "bitcount",
        "history": [Step(thought="try a", action="edit_file(...)", observation="FAIL")],
        "attempt": 1,
        "test_result": {"passed": False, "output": "AssertionError", "timed_out": False},
        "new_reflections": [],
    }
    out = nodes.reflect(state, chat=fake_chat)
    assert out["new_reflections"] == ["Lesson: check the base case."]


def test_persist_writes_all_new_reflections():
    fake_store = MagicMock()
    state: AgentState = {
        "bug_name": "bitcount",
        "new_reflections": ["Lesson: a", "Lesson: b"],
    }
    nodes.persist(state, store=fake_store)
    assert fake_store.add.call_count == 2