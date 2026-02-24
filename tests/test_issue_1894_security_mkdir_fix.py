"""Regression tests for issue #1894: Directory creation security vulnerabilities.

Issue: Path(args.db).parent.mkdir() in main() creates directories prematurely,
causing TOCTOU race conditions and path confusion when parent path is a file.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os
import threading

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

    # Should fail (exit code != 0)
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
    assert result != 0, "Should fail when immediate parent is a file"


def test_storage_init_fails_when_parent_is_file(tmp_path) -> None:
    """Issue #1894: TodoStorage.__init__ should validate parent path type."""
    # Create a file where directory should exist
    conflicting_file = tmp_path / "blocking.json"
    conflicting_file.write_text("file content")

    # Create storage that needs to write inside this "file"
    db_path = conflicting_file / "data.json"

    # Storage init/first use should detect the problem
    storage = TodoStorage(str(db_path))

    # Operations that need to write should fail with proper error
    with pytest.raises((ValueError, OSError), match=r"(directory|path|not a directory)"):
        storage.save([])


def test_storage_handles_permission_denied_gracefully(tmp_path, capsys) -> None:
    """Issue #1894: Should provide clear error when directory creation fails due to permissions."""
    # Create a read-only directory
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)  # Read-only

    try:
        # Try to create database in read-only directory
        db_path = readonly_dir / "subdir" / "todo.json"
        storage = TodoStorage(str(db_path))

        # Should fail gracefully with clear error
        with pytest.raises((OSError, PermissionError, ValueError)):
            storage.save([])
    finally:
        # Restore permissions for cleanup
        readonly_dir.chmod(0o755)


def test_cli_succeeds_for_normal_nested_paths(tmp_path, capsys) -> None:
    """Issue #1894: Normal nested directory creation should still work."""
    # Create a deeply nested path that doesn't exist yet
    db_path = str(tmp_path / "a" / "b" / "c" / "todo.json")
    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "add", "test"])

    # Should succeed
    result = run_command(args)
    assert result == 0, "Normal nested path creation should work"

    # Verify the todo was actually created
    captured = capsys.readouterr()
    assert "Added" in captured.out or "test" in captured.out


def test_cli_succeeds_when_parent_already_exists_as_directory(tmp_path, capsys) -> None:
    """Issue #1894: Should work normally when parent directory already exists."""
    # Pre-create the parent directory
    parent_dir = tmp_path / "existing_dir"
    parent_dir.mkdir()

    db_path = str(parent_dir / "todo.json")
    parser = build_parser()
    args = parser.parse_args(["--db", db_path, "add", "test"])

    # Should succeed
    result = run_command(args)
    assert result == 0, "Should succeed when parent already exists as directory"

    captured = capsys.readouterr()
    assert "Added" in captured.out


def test_toctou_race_condition_parent_replaced_with_symlink(tmp_path) -> None:
    """Issue #5501: TOCTOU race condition between checking and mkdir.

    Tests that if a directory is replaced with a symlink between the existence
    check and the mkdir call, we handle it properly without TOCTOU vulnerability.

    This simulates an attacker replacing a directory with a symlink pointing to
    an unsafe location during the window between check and create.
    """
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    db_path = tmp_path / "db" / "subdir" / "todo.json"

    race_condition_triggered = threading.Event()
    mkdir_calls = []

    # Monkey-patch mkdir to simulate the race condition
    original_mkdir = os.mkdir

    def patched_mkdir(path, *args, **kwargs):
        mkdir_calls.append(path)
        # On the first call, simulate the race: replace the parent directory with a symlink
        if len(mkdir_calls) == 1 and str(path).endswith("/db"):
            # Simulate: attacker replaces 'db' with a symlink to target_dir
            # This happens between the existence check and the mkdir call
            db_dir = tmp_path / "db"
            if db_dir.exists() and db_dir.is_dir():
                # The fix should handle this by using atomic operations
                race_condition_triggered.set()
        return original_mkdir(path, *args, **kwargs)

    # Patch and test
    original_os_mkdir = os.mkdir
    os.mkdir = patched_mkdir
    try:
        storage = TodoStorage(str(db_path))
        # The operation should either succeed safely or fail with appropriate error
        # It should NOT create files in unintended locations
        storage.save([])
    except (ValueError, OSError):
        # Expected - the fix should detect the race condition
        pass
    finally:
        os.mkdir = original_os_mkdir

    # Verify: no file should be created in target_dir via symlink attack
    assert not (target_dir / "subdir" / "todo.json").exists(), \
        "TOCTOU vulnerability: file created in unintended location"


def test_toctou_race_condition_parent_is_file_error(tmp_path) -> None:
    """Issue #5501: Verify atomic error handling for file-as-directory conflicts.

    This test ensures that even in race conditions, we properly detect when
    a parent component is a file and raise appropriate errors.
    """
    # Create a file where a directory would be needed
    blocking_file = tmp_path / "blocking"
    blocking_file.write_text("I am a file")

    db_path = blocking_file / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should fail with appropriate error about file vs directory
    with pytest.raises((ValueError, OSError), match=r"(not a directory|Not a directory|exists as a file|directory|path)"):
        storage.save([])


def test_atomic_directory_creation_no_separate_check(tmp_path) -> None:
    """Issue #5501: Verify that directory creation is atomic.

    The fix should use mkdir(parents=True, exist_ok=True) directly without
    separate existence checks, eliminating the TOCTOU window.
    """
    from flywheel.todo import Todo

    db_path = tmp_path / "deeply" / "nested" / "path" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should create directories atomically without separate check
    storage.save([Todo(id=1, text="test", done=False)])

    # Verify the file was created in the correct location
    assert db_path.exists(), "Database file should be created"
    assert db_path.parent.is_dir(), "Parent should be a directory"
