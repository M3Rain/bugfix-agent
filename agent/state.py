"""LangGraph state container.

We keep this in its own module so node and graph code can import it without
pulling in chroma / ollama at import time. `TestResult` lives in tools.py
(it's the return type of run_tests); we import it here to avoid duplication."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

from typing_extensions import TypedDict

from agent.tools import TestResult


@dataclass
class Step:
    thought: str
    action: str          # e.g. 'edit_file(path="bitcount.py", old="...", new="...")'
    observation: str


class AgentState(TypedDict, total=False):
    # task
    bug_name: str
    test_file: str
    sandbox_dir: str

    # short-term scratchpad
    history: list[Step]
    attempt: int
    max_attempts: int
    last_tool: str          # tool name run by the most recent Act (routing hint)
    tested: bool            # did the most recent Act actually run the suite?

    # long-term reflexion memory
    retrieved_reflections: list[str]
    new_reflections: list[str]

    # outcome
    test_result: TestResult
    status: Literal["running", "success", "failed"]