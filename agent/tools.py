"""Sandboxed file + test tools used by the Act node."""
from __future__ import annotations
from pathlib import Path
import os
import shutil
import subprocess
from typing_extensions import TypedDict


def read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {path}")
    return p.read_text()

class EditError(RuntimeError):
    """Raised when an edit cannot be applied unambiguously."""


def edit_file(path: str, old: str, new: str) -> None:
    """Replace the unique occurrence of `old` with `new` in `path`.

    Raises EditError if `old` is not found or occurs more than once.
    """
    p = Path(path)
    text = p.read_text()
    occurrences = text.count(old)
    if occurrences == 0:
        raise EditError(f"old string not found in {path}: {old!r}")
    if occurrences > 1:
        raise EditError(
            f"old string is ambiguous ({occurrences} matches) in {path}"
        )
    p.write_text(text.replace(old, new, 1))


class TestResult(TypedDict):
    passed: bool
    output: str
    timed_out: bool


def _data_dir() -> Path:
    return Path(os.environ.get("BUGFIX_DATA_DIR", "data/quixbugs"))


def _workdir() -> Path:
    return Path(os.environ.get("BUGFIX_WORKDIR", "workdir"))


# Minimal stand-in for QuixBugs' repo-root conftest, used only when the
# vendored one is absent. Defines the same options/flags the tests + run_tests
# rely on so any sandbox can be collected by pytest.
_FALLBACK_CONFTEST = '''import pytest


def pytest_addoption(parser):
    parser.addoption("--correct", action="store_true", default=False)
    parser.addoption("--runslow", action="store_true", default=False)


def pytest_configure(config):
    pytest.use_correct = config.getoption("--correct")
    pytest.run_slow = config.getoption("--runslow")
'''


def sandbox_path(bug_name: str) -> Path:
    """Return the per-bug sandbox directory (does not create it)."""
    return _workdir() / bug_name


def program_path(bug_name: str) -> Path:
    """Absolute path to the buggy file the agent edits inside the sandbox.

    QuixBugs tests do `from python_programs.<bug> import <bug>`, so the file
    must live at python_programs/<bug>.py — that is also the path the agent
    passes to read_file / edit_file.
    """
    return sandbox_path(bug_name) / "python_programs" / f"{bug_name}.py"


def prepare_sandbox(bug_name: str) -> Path:
    """Rebuild QuixBugs' real on-disk layout inside a fresh per-bug sandbox.

    Layout produced (so the vendored tests run unmodified):

        <sandbox>/
          conftest.py                       # defines pytest.use_correct
          json_testcases/<bug>.json         # inputs (JSON-driven bugs)
          python_programs/<bug>.py          # the buggy file the agent edits
          python_programs/node.py           # graph helper (if present)
          python_testcases/load_testdata.py
          python_testcases/node.py
          python_testcases/test_<bug>.py
    """
    data = _data_dir()
    sb = sandbox_path(bug_name)
    if sb.exists():
        shutil.rmtree(sb)

    progs_dir = sb / "python_programs"
    tests_dir = sb / "python_testcases"
    json_dir = sb / "json_testcases"
    for d in (progs_dir, tests_dir, json_dir):
        d.mkdir(parents=True)

    src_prog = data / "programs" / f"{bug_name}.py"
    src_test = data / "tests" / f"test_{bug_name}.py"
    if not src_prog.exists():
        raise FileNotFoundError(src_prog)
    if not src_test.exists():
        raise FileNotFoundError(src_test)

    # Buggy program (the only writable surface the agent touches).
    shutil.copy(src_prog, progs_dir / f"{bug_name}.py")
    # node.py is imported by graph programs and by graph tests.
    src_node = data / "programs" / "node.py"
    if src_node.exists():
        shutil.copy(src_node, progs_dir / "node.py")
        shutil.copy(src_node, tests_dir / "node.py")

    # Test harness.
    shutil.copy(src_test, tests_dir / f"test_{bug_name}.py")
    src_loader = data / "tests" / "load_testdata.py"
    if src_loader.exists():
        shutil.copy(src_loader, tests_dir / "load_testdata.py")

    # JSON-lines inputs (load_testdata resolves ../json_testcases/<bug>.json).
    src_json = data / "testcases" / f"{bug_name}.json"
    if src_json.exists():
        shutil.copy(src_json, json_dir / f"{bug_name}.json")

    # conftest defines pytest.use_correct (False -> import the buggy program)
    # and the --correct / --runslow options run_tests passes. Use the vendored
    # QuixBugs conftest when present; otherwise write a minimal equivalent so
    # the sandbox is always self-consistent (e.g. for unit-test fixtures).
    src_conftest = data / "conftest.py"
    if src_conftest.exists():
        shutil.copy(src_conftest, sb / "conftest.py")
    else:
        (sb / "conftest.py").write_text(_FALLBACK_CONFTEST)

    return sb


def run_tests(bug_name: str, timeout: int = 10) -> TestResult:
    """Run the vendored QuixBugs test for `bug_name` from the sandbox root."""
    sb = sandbox_path(bug_name)
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", f"python_testcases/test_{bug_name}.py",
             "-q", "--tb=short", "--runslow"],
            cwd=sb,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "passed": proc.returncode == 0,
            "output": (proc.stdout + proc.stderr)[-3000:],   # cap for prompt
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "passed": False,
            "output": f"TIMEOUT after {timeout}s\n{(e.stdout or '')[-1500:]}",
            "timed_out": True,
        }