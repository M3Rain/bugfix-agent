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


def sandbox_path(bug_name: str) -> Path:
    """Return the per-bug sandbox directory (does not create it)."""
    return _workdir() / bug_name


def prepare_sandbox(bug_name: str) -> Path:
    """Copy the buggy program + its test into a fresh sandbox directory."""
    sb = sandbox_path(bug_name)
    if sb.exists():
        shutil.rmtree(sb)
    sb.mkdir(parents=True)

    src_prog = _data_dir() / "programs" / f"{bug_name}.py"
    src_test = _data_dir() / "tests" / f"test_{bug_name}.py"
    if not src_prog.exists():
        raise FileNotFoundError(src_prog)
    if not src_test.exists():
        raise FileNotFoundError(src_test)
    shutil.copy(src_prog, sb / f"{bug_name}.py")
    shutil.copy(src_test, sb / f"test_{bug_name}.py")

    # Copy any shared JSON inputs QuixBugs needs (graphs, weighted_edges, etc.)
    for extra in (_data_dir() / "programs").glob("*.json"):
        shutil.copy(extra, sb / extra.name)
    return sb


def run_tests(bug_name: str, timeout: int = 10) -> TestResult:
    """Run pytest on the sandboxed test for `bug_name`."""
    sb = sandbox_path(bug_name)
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", f"test_{bug_name}.py", "-q", "--tb=short"],
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
            "output": f"TIMEOUT after {timeout}s\n{(e.stdout or b'').decode()[-1500:]}",
            "timed_out": True,
        }