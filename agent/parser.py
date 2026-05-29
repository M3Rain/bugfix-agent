"""Parse a single 'Action:' line produced by the LLM into a structured call.

We avoid `eval()` / `ast.literal_eval` on arbitrary LLM output for safety,
and instead use a small recursive descent on quoted-string kwargs."""
from __future__ import annotations
import re

ALLOWED_TOOLS = {"read_file", "edit_file", "run_tests", "finish"}

_NAME_RE = re.compile(r"\s*([A-Za-z_]\w*)\s*\(")


class ParseError(ValueError):
    pass


def _parse_kwargs(s: str) -> dict[str, str]:
    """Parse k1="v1", k2="v2"  where values may contain escaped quotes and newlines."""
    args: dict[str, str] = {}
    i = 0
    s = s.strip()
    while i < len(s):
        # key
        m = re.match(r'([A-Za-z_]\w*)\s*=\s*"', s[i:])
        if not m:
            raise ParseError(f"expected key= at offset {i}: {s[i:i+30]!r}")
        key = m.group(1)
        i += m.end()
        # value: read until unescaped quote
        buf: list[str] = []
        while i < len(s):
            ch = s[i]
            if ch == "\\" and i + 1 < len(s):
                buf.append(s[i + 1])
                i += 2
                continue
            if ch == '"':
                i += 1
                break
            buf.append(ch)
            i += 1
        else:
            raise ParseError("unterminated string")
        args[key] = "".join(buf)
        # comma or end
        while i < len(s) and s[i] in " ,\t\n":
            i += 1
    return args


def parse_action(text: str) -> dict:
    text = text.strip()
    m = _NAME_RE.match(text)
    if not m or not text.endswith(")"):
        raise ParseError(f"not a tool call: {text!r}")
    name = m.group(1)
    if name not in ALLOWED_TOOLS:
        raise ParseError(f"unknown tool: {name}")
    body = text[m.end():-1].strip()
    args = _parse_kwargs(body) if body else {}
    return {"tool": name, "args": args}