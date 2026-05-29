"""Sandboxed file + test tools used by the Act node."""
from __future__ import annotations
from pathlib import Path


def read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {path}")
    return p.read_text()