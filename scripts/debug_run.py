"""Throwaway diagnostic: run the agent on one bug and dump the full trace.

Usage (from project root):
    python scripts/debug_run.py bitcount
"""
import sys
from pathlib import Path

# Allow running as a plain script from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.graph import run


def main() -> None:
    bug = sys.argv[1] if len(sys.argv) > 1 else "bitcount"
    final = run(bug, max_attempts=6)

    print("\n" + "=" * 70)
    print(f"BUG: {bug}   STATUS: {final.get('status')}")
    print("=" * 70)

    for i, step in enumerate(final.get("history") or [], 1):
        print(f"\n--- Step {i} ---")
        print(f"THOUGHT : {step.thought!r}")
        print(f"ACTION  : {step.action!r}")
        obs = step.observation or ""
        print(f"OBSERVE : {obs[:600]}")

    print("\n" + "-" * 70)
    print("RETRIEVED REFLECTIONS:", final.get("retrieved_reflections"))
    print("NEW REFLECTIONS:")
    for r in final.get("new_reflections") or []:
        print("  -", r[:300])
    tr = final.get("test_result") or {}
    print("FINAL test_result.passed:", tr.get("passed"))


if __name__ == "__main__":
    main()
