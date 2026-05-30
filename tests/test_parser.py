import pytest
from agent.parser import parse_action, ParseError


def test_parse_read_file():
    out = parse_action('read_file(path="bitcount.py")')
    assert out == {"tool": "read_file", "args": {"path": "bitcount.py"}}


def test_parse_run_tests():
    out = parse_action("run_tests()")
    assert out == {"tool": "run_tests", "args": {}}


def test_parse_finish():
    out = parse_action("finish()")
    assert out == {"tool": "finish", "args": {}}


def test_parse_edit_file_multiline():
    raw = 'edit_file(path="a.py", old="x = 1\nx = 2", new="x = 99\nx = 2")'
    out = parse_action(raw)
    assert out["tool"] == "edit_file"
    assert out["args"]["old"] == "x = 1\nx = 2"
    assert out["args"]["new"] == "x = 99\nx = 2"


def test_parse_decodes_backslash_escapes():
    # The LLM emits the two characters backslash + n, which must decode to a
    # real newline so edit_file `old` can match the file's actual contents.
    raw = r'edit_file(path="a.py", old="n ^= n - 1\n        count += 1", new="n &= n - 1\n        count += 1")'
    out = parse_action(raw)
    assert out["args"]["old"] == "n ^= n - 1\n        count += 1"
    assert out["args"]["new"] == "n &= n - 1\n        count += 1"


def test_parse_bad_format_raises():
    with pytest.raises(ParseError):
        parse_action("here is not a tool call")