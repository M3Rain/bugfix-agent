"""Download QuixBugs (Python) into data/quixbugs/.

QuixBugs ships buggy programs in python_programs/ and reference correct
programs in correct_python_programs/. We copy the buggy ones plus the
testcases/ folder."""
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
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "clone", "--depth", "1", REPO, tmp], check=True)
        src = Path(tmp)
        (DEST / "programs").mkdir(exist_ok=True)
        (DEST / "tests").mkdir(exist_ok=True)
        for p in (src / "python_programs").glob("*.py"):
            if p.name.endswith("_test.py"):
                continue
            shutil.copy(p, DEST / "programs" / p.name)
        for p in (src / "python_testcases").glob("test_*.py"):
            shutil.copy(p, DEST / "tests" / p.name)
        # JSON files needed by some tests (e.g. node.py used by graph bugs)
        for p in (src / "python_programs").glob("*.json"):
            shutil.copy(p, DEST / "programs" / p.name)

    names = sorted(p.stem for p in (DEST / "programs").glob("*.py")
                   if not p.stem.startswith("_") and p.stem != "node")
    (DEST / "index.json").write_text(json.dumps(names, indent=2))
    print(f"Vendored {len(names)} bugs into {DEST}")


if __name__ == "__main__":
    main()