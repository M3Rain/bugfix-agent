from pathlib import Path
import pytest
from agent.tools import read_file
from agent.tools import edit_file, EditError

def test_read_file_returns_contents(tmp_path):
    f = tmp_path / "hello.py"
    f.write_text("print('hi')\n")
    assert read_file(str(f)) == "print('hi')\n"


def test_read_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_file(str(tmp_path / "missing.py"))




def test_edit_file_replaces_exact_match(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\ny = 2\n")
    edit_file(str(f), "x = 1", "x = 99")
    assert f.read_text() == "x = 99\ny = 2\n"


def test_edit_file_no_match_raises(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    with pytest.raises(EditError, match="not found"):
        edit_file(str(f), "z = 0", "z = 1")


def test_edit_file_ambiguous_match_raises(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\nx = 1\n")
    with pytest.raises(EditError, match="ambiguous"):
        edit_file(str(f), "x = 1", "x = 2")