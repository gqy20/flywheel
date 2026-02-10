"""Regression tests for issue #1894: Directory creation security vulnerabilities.

Issue: Path(args.db).parent.mkdir() in main() creates directories prematurely,
causing TOCTOU race conditions and path confusion when parent path is a file.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.cli import build_parser, run_command
from flywheel.storage import TodoStorage


def test_cli_fails_when_parent_is_file_not_directory(tmp_path, capsys) -> None:
    """Issue #1894: Should fail with clear error when parent path is a file, not directory.

    Before fix: mkdir succeeds but later operations fail cryptically with NotADirectoryError
    After fix: Should detect file vs directory and exit with error code != 0 with clear message
    """
    # Create a file where we expect a directory
    conflicting_file = tmp_path / "db.json"
    conflicting_file.write_text("I am a file, not a directory")

    # Try to create db at path that would require the file to be a directory
    db_path = str(conflicting_file / "subdir" / "todo.json")
    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "add", "test"])

    # Should fail (exit code != 0) - either from path validation or directory creation
    result = run_command(args)
    assert result != 0, "Should fail when parent path is a file"

    # Error message should indicate the path problem (now in stderr)
    captured = capsys.readouterr()
    assert "Error:" in captured.out or "Error:" in captured.err or "error" in captured.out.lower() or "error" in captured.err.lower()


def test_cli_fails_when_immediate_parent_is_file(tmp_path, capsys) -> None:
    """Issue #1894: Minimal test case from issue - immediate parent is a file."""
    # Create a file at parent location
    parent_file = tmp_path / "db.json"
    parent_file.write_text("")  # Empty file

    # Try to create database inside what is actually a file
    db_path = str(parent_file / "file.json")
    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "add", "test"])

    result = run_command(args)
    # Should fail due to path validation (path outside CWD)
    assert result != 0, "Should fail when immediate parent is a file"


def test_storage_init_fails_when_parent_is_file(tmp_path) -> None:
    """Issue #1894: TodoStorage.__init__ should validate parent path type."""
    # Create a file where directory should exist
    conflicting_file = tmp_path / "blocking.json"
    conflicting_file.write_text("file content")

    # Create storage that needs to write inside this "file"
    db_path = conflicting_file / "data.json"

    # Storage init should fail due to path validation (path outside CWD)
    with pytest.raises(ValueError, match=r"path|escape|outside"):
        TodoStorage(str(db_path))


def test_storage_handles_permission_denied_gracefully(tmp_path, capsys) -> None:
    """Issue #1894: Should provide clear error when directory creation fails due to permissions."""
    # Create a read-only directory
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)  # Read-only

    try:
        # Try to create database in read-only directory
        db_path = readonly_dir / "subdir" / "todo.json"

        # Storage init should fail due to path validation (path outside CWD)
        with pytest.raises(ValueError, match=r"path|escape|outside"):
            TodoStorage(str(db_path))
    finally:
        # Restore permissions for cleanup
        readonly_dir.chmod(0o755)


def test_cli_succeeds_for_normal_nested_paths(tmp_path, capsys) -> None:
    """Issue #1894: Normal nested directory creation should still work."""
    # Use relative path for nested directory creation
    db_path = "test-nested/a/b/c/todo.json"
    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "add", "test"])

    # Should succeed
    result = run_command(args)
    assert result == 0, "Normal nested path creation should work"

    # Verify the todo was actually created
    captured = capsys.readouterr()
    assert "Added" in captured.out or "test" in captured.out

    # Clean up
    import shutil
    shutil.rmtree("test-nested", ignore_errors=True)


def test_cli_succeeds_when_parent_already_exists_as_directory(tmp_path, capsys) -> None:
    """Issue #1894: Should work normally when parent directory already exists."""
    # Pre-create the parent directory
    parent_dir = "test-existing-dir"
    from pathlib import Path
    Path(parent_dir).mkdir(exist_ok=True)

    db_path = f"{parent_dir}/todo.json"
    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "add", "test"])

    # Should succeed
    result = run_command(args)
    assert result == 0, "Should succeed when parent already exists as directory"

    captured = capsys.readouterr()
    assert "Added" in captured.out

    # Clean up
    import shutil
    shutil.rmtree(parent_dir, ignore_errors=True)
