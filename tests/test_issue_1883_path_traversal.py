"""Regression tests for issue #1883: Path traversal vulnerability via user-controlled db_path.

Issue: The --db argument accepts arbitrary paths including '../' sequences and
absolute paths outside the working directory, allowing potential access to
sensitive system files.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.cli import build_parser, run_command
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_rejects_path_traversal_with_parent_dot_dot() -> None:
    """Issue #1883: Path with '../' sequences should be rejected.

    Before fix: Accepts paths like '../../../etc/passwd'
    After fix: Should reject paths containing '..' components
    """
    with pytest.raises(ValueError, match=r"path|escape|outside|invalid"):
        storage = TodoStorage("../../../etc/passwd")
        storage.load()


def test_storage_rejects_absolute_path_outside_cwd() -> None:
    """Issue #1883: Absolute paths outside current directory should be rejected.

    Before fix: Accepts absolute paths like '/tmp/test.json' or '/etc/passwd'
    After fix: Should reject absolute paths that escape the working directory
    """
    with pytest.raises(ValueError, match=r"path|escape|outside|invalid|absolute"):
        storage = TodoStorage("/etc/passwd")
        storage.load()


def test_storage_accepts_safe_relative_path() -> None:
    """Issue #1883: Safe relative paths within current directory should work.

    Before fix: Works
    After fix: Should still work
    """
    storage = TodoStorage(".todo.json")
    todos = storage.load()
    assert todos == []


def test_storage_accepts_safe_subdirectory_path() -> None:
    """Issue #1883: Safe subdirectory paths should be accepted.

    Before fix: Works
    After fix: Should still work
    """
    storage = TodoStorage("subdir/todo.json")
    # Loading non-existent file returns empty list
    todos = storage.load()
    assert todos == []


def test_cli_rejects_path_traversal_argument(capsys) -> None:
    """Issue #1883: CLI --db argument with path traversal should be rejected.

    Before fix: Accepts --db="../../../etc/passwd"
    After fix: Should reject with error message
    """
    parser = build_parser()
    args = parser.parse_args(["--db", "../../../etc/passwd", "list"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "error" in captured.out.lower() or "error" in captured.err.lower()


def test_cli_rejects_absolute_path_argument(capsys) -> None:
    """Issue #1883: CLI --db with absolute path outside cwd should be rejected.

    Before fix: Accepts --db="/etc/passwd"
    After fix: Should reject with error message
    """
    parser = build_parser()
    args = parser.parse_args(["--db", "/etc/passwd", "list"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "error" in captured.out.lower() or "error" in captured.err.lower()


def test_cli_accepts_safe_db_path(tmp_path, capsys) -> None:
    """Issue #1883: CLI --db with safe path should still work.

    Before fix: Works
    After fix: Should still work with relative path within CWD.
    For security, absolute paths outside CWD are rejected.
    """
    # Use a relative path within CWD for testing, not tmp_path absolute path
    db = "test-safe-todo.json"
    parser = build_parser()

    args = parser.parse_args(["--db", db, "add", "test todo"])
    assert run_command(args) == 0

    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0

    captured = capsys.readouterr()
    assert "test todo" in captured.out

    # Clean up
    Path(db).unlink(missing_ok=True)


def test_cli_accepts_subdirectory_db_path(tmp_path, capsys) -> None:
    """Issue #1883: CLI --db with subdirectory path should work.

    Before fix: Works
    After fix: Should still work with relative path within CWD.
    For security, absolute paths outside CWD are rejected.
    """
    # Use a relative path within CWD for testing, not tmp_path absolute path
    db = "test-subdir/todo.json"
    parser = build_parser()

    args = parser.parse_args(["--db", db, "add", "subdir todo"])
    assert run_command(args) == 0

    captured = capsys.readouterr()
    assert "subdir todo" in captured.out

    # Clean up
    import shutil
    shutil.rmtree("test-subdir", ignore_errors=True)


def test_storage_save_with_safe_path_works(tmp_path) -> None:
    """Issue #1883: Save operation should work with safe paths.

    Before fix: Works
    After fix: Should still work with relative paths within CWD.
    For security, absolute paths outside CWD are rejected.
    """
    # Use a relative path within CWD for testing, not tmp_path absolute path
    db = "test-save-safe-todo.json"
    storage = TodoStorage(db)

    todos = [Todo(id=1, text="safe todo")]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "safe todo"

    # Clean up
    Path(db).unlink(missing_ok=True)


def test_storage_rejects_complex_path_traversal() -> None:
    """Issue #1883: Complex path traversal sequences should be rejected.

    Before fix: Accepts paths like './subdir/../../etc/passwd'
    After fix: Should reject any path that escapes the base directory
    """
    with pytest.raises(ValueError, match=r"path|escape|outside|invalid"):
        storage = TodoStorage("./subdir/../../etc/passwd")
        storage.load()


def test_storage_rejects_path_traversal_in_middle(tmp_path) -> None:
    """Issue #1883: Path traversal in middle components should be rejected.

    Before fix: May accept paths like 'safe/../../etc/passwd'
    After fix: Should reject paths with '..' at any level
    """
    with pytest.raises(ValueError, match=r"path|escape|outside|invalid"):
        storage = TodoStorage("safe/../../etc/passwd")
        storage.load()
