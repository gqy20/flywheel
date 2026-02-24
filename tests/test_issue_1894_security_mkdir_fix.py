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

    # Should fail (exit code != 0)
    result = run_command(args)
    assert result != 0, "Should fail when parent path is a file"

    # Error message should indicate the path problem (now in stderr)
    captured = capsys.readouterr()
    assert (
        "Error:" in captured.out
        or "Error:" in captured.err
        or "error" in captured.out.lower()
        or "error" in captured.err.lower()
    )


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


def test_concurrent_parent_directory_creation_no_race(tmp_path) -> None:
    """Issue #5461: TOCTOU race condition in _ensure_parent_directory.

    Tests that concurrent creation of the same parent directory by multiple
    processes does not cause FileExistsError. The race occurs between
    the parent.exists() check and parent.mkdir(exist_ok=False) call.

    Before fix: FileExistsError when another process creates the directory
    After fix: Should succeed silently with exist_ok=True
    """
    import multiprocessing
    import time

    # All processes will try to create db at same nested path
    db_path = tmp_path / "shared" / "nested" / "db.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that tries to save to same nested path concurrently."""
        try:
            # Small random delay to synchronize start time
            time.sleep(0.01 * (worker_id % 3))

            storage = TodoStorage(str(db_path))
            # This triggers _ensure_parent_directory which has the TOCTOU window
            storage.save([])

            result_queue.put(("success", worker_id))
        except FileExistsError as e:
            # This is the bug - FileExistsError from mkdir(exist_ok=False)
            result_queue.put(("race_bug", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently targeting same new directory
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    race_bugs = [r for r in results if r[0] == "race_bug"]
    errors = [r for r in results if r[0] == "error"]

    # The fix should prevent FileExistsError (race_bugs)
    assert len(race_bugs) == 0, (
        f"TOCTOU race detected: {len(race_bugs)} workers hit FileExistsError. Details: {race_bugs}"
    )

    # At least some should succeed
    assert len(successes) > 0, f"Expected some successes, got errors: {errors}"

    # No other errors should occur
    assert len(errors) == 0, f"Workers encountered unexpected errors: {errors}"
