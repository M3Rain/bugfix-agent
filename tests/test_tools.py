from pathlib import Path
import pytest
from agent.tools import read_file


def test_read_file_returns_contents(tmp_path):
    f = tmp_path / "hello.py"
    f.write_text("print('hi')\n")
    assert read_file(str(f)) == "print('hi')\n"


def test_read_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_file(str(tmp_path / "missing.py"))