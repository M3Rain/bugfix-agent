from pathlib import Path
import pytest
from agent.tools import read_file
from agent.tools import edit_file, EditError
from agent.tools import prepare_sandbox, run_tests, sandbox_path


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

def test_prepare_sandbox_copies_program_and_tests(tmp_path, monkeypatch):
    # arrange a fake dataset
    monkeypatch.setenv("BUGFIX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BUGFIX_WORKDIR", str(tmp_path / "wd"))
    (tmp_path / "data" / "programs").mkdir(parents=True)
    (tmp_path / "data" / "tests").mkdir(parents=True)
    (tmp_path / "data" / "programs" / "bitcount.py").write_text("def bitcount(n):\n    return 0\n")
    (tmp_path / "data" / "tests" / "test_bitcount.py").write_text(
        "from bitcount import bitcount\n"
        "def test_bc():\n"
        "    assert bitcount(3) == 2\n"
    )

    sb = prepare_sandbox("bitcount")
    # QuixBugs layout: program under python_programs/, test under python_testcases/.
    assert (sb / "python_programs" / "bitcount.py").exists()
    assert (sb / "python_testcases" / "test_bitcount.py").exists()


def test_run_tests_detects_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("BUGFIX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BUGFIX_WORKDIR", str(tmp_path / "wd"))
    (tmp_path / "data" / "programs").mkdir(parents=True)
    (tmp_path / "data" / "tests").mkdir(parents=True)
    (tmp_path / "data" / "programs" / "x.py").write_text("def x(): return 0\n")
    (tmp_path / "data" / "tests" / "test_x.py").write_text(
        "from python_programs.x import x\n"
        "def test_x():\n"
        "    assert x() == 1\n"
    )
    prepare_sandbox("x")
    result = run_tests("x")
    assert result["passed"] is False
    assert "assert 0 == 1" in result["output"] or "AssertionError" in result["output"]


def test_run_tests_detects_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("BUGFIX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BUGFIX_WORKDIR", str(tmp_path / "wd"))
    (tmp_path / "data" / "programs").mkdir(parents=True)
    (tmp_path / "data" / "tests").mkdir(parents=True)
    (tmp_path / "data" / "programs" / "y.py").write_text("def y(): return 1\n")
    (tmp_path / "data" / "tests" / "test_y.py").write_text(
        "from python_programs.y import y\n"
        "def test_y():\n"
        "    assert y() == 1\n"
    )
    prepare_sandbox("y")
    result = run_tests("y")
    assert result["passed"] is True