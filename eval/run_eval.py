"""
Usage:
    python eval/run_eval.py --mode headline
    python eval/run_eval.py --mode ablation
    python eval/run_eval.py --mode accumulation
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import shutil
import time
from pathlib import Path

from agent.graph import run, build_graph
from agent import tools as tool_mod
from agent.memory import ReflectionStore

DATA = Path("data/quixbugs")
RESULTS = Path("eval/results")


def _all_bugs() -> list[str]:
    return json.loads((DATA / "index.json").read_text())


def _wipe_memory() -> None:
    if Path("memory_store").exists():
        shutil.rmtree("memory_store")


def _run_one(bug: str, max_attempts: int) -> dict:
    t0 = time.time()
    final = run(bug, max_attempts=max_attempts)
    return {
        "bug": bug,
        "passed": bool(final["test_result"]["passed"]),
        "attempts": len(final.get("history") or []),
        "wall_s": round(time.time() - t0, 2),
        "status": final["status"],
    }


def headline() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = [_run_one(b, 6) for b in _all_bugs()]
    out = RESULTS / "headline.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    pass_rate = sum(r["passed"] for r in rows) / len(rows)
    print(f"Pass rate: {pass_rate:.0%}   wrote {out}")


def ablation() -> None:
    """Run twice: once with reflexion (full graph), once without."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    bugs = _all_bugs()

    # With Reflexion
    _wipe_memory()
    with_results = [_run_one(b, 6) for b in bugs]

    # Without Reflexion — disable retrieve/reflect/persist via env flag
    _wipe_memory()
    os.environ["BUGFIX_DISABLE_REFLEXION"] = "1"
    try:
        without_results = [_run_one(b, 6) for b in bugs]
    finally:
        os.environ.pop("BUGFIX_DISABLE_REFLEXION", None)

    out = RESULTS / "ablation.csv"
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bug", "with_passed", "with_attempts", "without_passed", "without_attempts"])
        for a, b in zip(with_results, without_results):
            w.writerow([a["bug"], a["passed"], a["attempts"], b["passed"], b["attempts"]])
    print(f"wrote {out}")


def accumulation() -> None:
    """Run bugs sequentially from empty memory; track memory size + per-bug success."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    _wipe_memory()
    bugs = _all_bugs()
    store = ReflectionStore()
    rows = []
    for i, bug in enumerate(bugs, 1):
        mem_size_before = store._col.count()
        r = _run_one(bug, 6)
        rows.append({**r, "mem_size_before": mem_size_before, "i": i})
    out = RESULTS / "accumulation.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["headline", "ablation", "accumulation"], required=True)
    args = p.parse_args()
    {"headline": headline, "ablation": ablation, "accumulation": accumulation}[args.mode]()


if __name__ == "__main__":
    main()