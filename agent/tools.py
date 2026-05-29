"""Sandboxed file + test tools used by the Act node."""
from __future__ import annotations
from pathlib import Path



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