"""Regression tests for issue #1858: Path traversal vulnerability.

Issue: Path parameter can escape intended directory via '..' components.
The path parameter in TodoStorage is constructed from user input without
validation, allowing access to files outside the intended directory.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.cli import build_parser, run_command
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_rejects_path_traversal_with_dotdot(tmp_path) -> None:
    """Issue #1858: TodoStorage should reject paths with '..' that escape cwd.

    Before fix: Paths like '../../../etc/passwd' could access files outside intended directory
    After fix: Should raise ValueError when path would escape current working directory
    """
    # Create a path that tries to escape using '..'
    escaped_path = tmp_path / ".." / ".." / ".." / "etc" / "passwd"

    # This should fail with a clear security error
    storage = TodoStorage(str(escaped_path))

    with pytest.raises(ValueError, match=r"(escape|traversal|outside|directory|security)"):
        storage.save([])


def test_storage_normalizes_and_allows_subdirectory_paths(tmp_path, monkeypatch) -> None:
    """Issue #1858: Legitimate subdirectory paths should still work.

    After fix: Paths like './subdir/file.json' or 'subdir/file.json' should work correctly
    """
    # Change to tmp_path as cwd for this test
    monkeypatch.chdir(tmp_path)

    # Create a subdirectory path (legitimate use case)
    db_path = tmp_path / "subdir" / "todo.json"

    storage = TodoStorage(str(db_path))
    todos = [Todo(id=1, text="test")]

    # This should succeed - subdirectories are allowed
    storage.save(todos)

    # Verify the data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_storage_rejects_absolute_path_with_traversal_outside_base(tmp_path) -> None:
    """Issue #1858: TodoStorage should reject absolute paths with '..' that escape their base.

    Before fix: Paths like '/tmp/foo/../../../etc/passwd' could access files outside /tmp/foo
    After fix: Should raise ValueError when absolute path with '..' escapes intended base
    """
    # Use an absolute path with '..' that escapes its base directory
    absolute_path_with_traversal = Path("/tmp/safe_dir/../../../etc/passwd")

    storage = TodoStorage(str(absolute_path_with_traversal))

    with pytest.raises(ValueError, match=r"(escape|outside|directory|security|traversal)"):
        storage.save([])


def test_cli_rejects_path_traversal_db_argument(tmp_path, capsys, monkeypatch) -> None:
    """Issue #1858: CLI should reject --db argument with path traversal.

    Before fix: 'todo --db ../../../etc/passwd add test' could write to unintended location
    After fix: Should exit with error code != 0 and show security warning
    """
    # Change to tmp_path as cwd for this test
    monkeypatch.chdir(tmp_path)

    # Create a path that tries to escape using '..'
    db_path = "../../../etc/passwd"
    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "add", "test"])

    # Should fail with exit code != 0
    result = run_command(args)
    assert result != 0, "Should reject path traversal in --db argument"

    # Should show an error message
    captured = capsys.readouterr()
    error_output = captured.err.lower() + captured.out.lower()
    assert any(
        keyword in error_output
        for keyword in ["escape", "traversal", "outside", "security", "directory"]
    ), f"Expected security error in output, got: {captured.err} {captured.out}"


def test_cli_allows_subdirectory_db_argument(tmp_path, capsys, monkeypatch) -> None:
    """Issue #1858: CLI should allow --db argument with legitimate subdirectory paths.

    After fix: 'todo --db ./data/todo.json add test' should work correctly
    """
    # Change to tmp_path as cwd for this test
    monkeypatch.chdir(tmp_path)

    # Use a legitimate subdirectory path
    db_path = "./data/todo.json"
    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "add", "test todo"])

    # Should succeed
    result = run_command(args)
    assert result == 0, "Should allow subdirectory path in --db argument"

    # Verify the todo was created
    captured = capsys.readouterr()
    assert "Added" in captured.out


def test_storage_provides_clear_error_message_for_path_traversal(tmp_path) -> None:
    """Issue #1858: Error message should clearly explain the security issue.

    After fix: Error message should mention 'path traversal' or 'escapes' or 'outside'
    """
    escaped_path = tmp_path / ".." / ".." / "etc" / "passwd"
    storage = TodoStorage(str(escaped_path))

    try:
        storage.save([])
        pytest.fail("Expected ValueError for path traversal")
    except ValueError as e:
        error_msg = str(e).lower()
        assert any(
            keyword in error_msg
            for keyword in ["escape", "traversal", "outside", "security", "directory"]
        ), f"Error message should mention path traversal issue, got: {e}"
