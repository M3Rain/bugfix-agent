"""Download QuixBugs (Python) into data/quixbugs/.

QuixBugs ships buggy programs in python_programs/ and reference correct
programs in correct_python_programs/. Its tests are NOT standalone: each
test_<bug>.py imports either `load_testdata` (for the JSON-driven bugs) or
`node` (for the graph bugs), reads inputs from json_testcases/, and selects
the buggy-vs-correct program via the `pytest.use_correct` flag defined in the
repo-root conftest.py.

To make the suite runnable, we vendor the whole harness, not just the buggy
programs:

    data/quixbugs/
      programs/        <- buggy python_programs/*.py (incl. node.py)
      tests/           <- test_*.py + load_testdata.py + node.py
      testcases/       <- json_testcases/*.json
      conftest.py      <- repo-root conftest (defines pytest.use_correct)
      index.json       <- list of bug names

prepare_sandbox() (in agent/tools.py) reassembles these into QuixBugs' real
on-disk layout inside the per-bug sandbox.
"""
from __future__ import annotations
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = "https://github.com/jkoppel/QuixBugs.git"
DEST = Path(__file__).resolve().parents[1] / "data" / "quixbugs"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    programs = DEST / "programs"
    tests = DEST / "tests"
    testcases = DEST / "testcases"
    for d in (programs, tests, testcases):
        d.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "clone", "--depth", "1", REPO, tmp], check=True)
        src = Path(tmp)

        # Buggy programs (skip QuixBugs' own *_test.py helpers).
        for p in (src / "python_programs").glob("*.py"):
            if p.name.endswith("_test.py"):
                continue
            shutil.copy(p, programs / p.name)

        # Test files + the two helper modules the tests import directly.
        for p in (src / "python_testcases").glob("test_*.py"):
            shutil.copy(p, tests / p.name)
        for helper in ("load_testdata.py", "node.py"):
            hp = src / "python_testcases" / helper
            if hp.exists():
                shutil.copy(hp, tests / helper)

        # JSON-lines testcases consumed by load_testdata.load_json_testcases.
        for p in (src / "json_testcases").glob("*.json"):
            shutil.copy(p, testcases / p.name)

        # Repo-root conftest defines pytest.use_correct / pytest.run_slow.
        shutil.copy(src / "conftest.py", DEST / "conftest.py")

    names = sorted(p.stem for p in programs.glob("*.py")
                   if not p.stem.startswith("_") and p.stem != "node")
    (DEST / "index.json").write_text(json.dumps(names, indent=2))
    print(f"Vendored {len(names)} bugs into {DEST}")


if __name__ == "__main__":
    main()
