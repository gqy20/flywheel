"""Regression tests for issue #7175: TOCTOU race condition in _ensure_parent_directory.

Issue: Time-of-check to time-of-use (TOCTOU) race condition exists between
checking parent paths for files and creating directories. An attacker could
create a file at a parent path during this race window.

The fix uses exist_ok=True with try/except to catch FileExistsError which
indicates a file (not directory) was created at a parent path.

These tests verify the fix handles the race condition safely.
"""

from __future__ import annotations

import concurrent.futures

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory


def test_toctou_concurrent_directory_creation_succeeds(tmp_path) -> None:
    """Issue #7175: Multiple threads creating same directory should succeed.

    After the fix with exist_ok=True, concurrent directory creation should
    succeed without raising FileExistsError for legitimate directory creation.
    """
    db_path = tmp_path / "shared_parent" / "todo.json"
    success_count = []
    error_list = []

    def attempt_save():
        try:
            storage = TodoStorage(str(db_path))
            storage.save([])
            success_count.append(1)
        except Exception as e:
            error_list.append(e)

    # Run multiple concurrent saves
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_save) for _ in range(10)]
        concurrent.futures.wait(futures)

    # All should succeed (directory already exists is OK with exist_ok=True)
    assert len(success_count) == 10, (
        f"Expected 10 successes, got {len(success_count)}. Errors: {error_list}"
    )
    # Note: We don't check the loaded data because concurrent saves with empty lists
    # will overwrite each other. The important thing is no errors occurred.


def test_toctou_race_directory_exists_ok(tmp_path) -> None:
    """Issue #7175: Using exist_ok=True should handle directory-already-exists case.

    After the fix, mkdir should use exist_ok=True to handle the case where
    another thread created the same directory legitimately.
    """
    db_path = tmp_path / "parent" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Pre-create the parent directory
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # This should succeed without error
    storage.save([])

    # Verify data was saved
    assert db_path.exists()
    assert storage.load() == []


def test_toctou_file_at_parent_path_clear_error(tmp_path) -> None:
    """Issue #7175: If a file exists at parent path, error should be clear.

    When a file is created at a parent path, the error message should clearly
    indicate the problem (file vs directory conflict).
    """
    # Create a file where we need a directory
    blocking_file = tmp_path / "blocking"
    blocking_file.write_text("I am a file")

    db_path = blocking_file / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should fail with clear error about file vs directory
    with pytest.raises((ValueError, OSError, NotADirectoryError)) as exc_info:
        storage.save([])

    # Error message should mention the path issue
    error_msg = str(exc_info.value).lower()
    assert any(
        keyword in error_msg for keyword in ["file", "directory", "not a directory", "path"]
    ), f"Error message should explain file vs directory conflict: {exc_info.value}"


def test_toctou_nested_parent_file_conflict(tmp_path) -> None:
    """Issue #7175: Detect file at any parent level, not just immediate parent."""
    # Create nested structure with a file in the middle
    level1 = tmp_path / "level1"
    level1.mkdir()

    # Create a file at level1/level2 (should be a directory)
    blocking_file = level1 / "level2"
    blocking_file.write_text("I block this path")

    # Try to create db at level1/level2/level3/todo.json
    db_path = blocking_file / "level3" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should fail with clear error
    with pytest.raises((ValueError, OSError, NotADirectoryError)):
        storage.save([])


def test_toctou_mkdir_fileexistserror_when_file_blocks_path(tmp_path) -> None:
    """Issue #7175: mkdir with exist_ok=True should catch FileExistsError for files.

    When mkdir(parents=True, exist_ok=True) encounters a file at a parent path,
    it raises FileExistsError (not NotADirectoryError). The fix should catch this
    and provide a clear error message.
    """
    # Create a file where we need a directory
    blocking_file = tmp_path / "blocking"
    blocking_file.write_text("I am a file")

    # Try to create a nested path that would require the file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"

    # The _ensure_parent_directory function should raise a clear error
    with pytest.raises((ValueError, OSError, FileExistsError)) as exc_info:
        _ensure_parent_directory(db_path)

    # Error should mention the blocking path
    error_msg = str(exc_info.value)
    assert (
        "blocking" in error_msg.lower()
        or "file" in error_msg.lower()
        or "directory" in error_msg.lower()
    )


def test_toctou_normal_operation_after_fix(tmp_path) -> None:
    """Issue #7175: Normal save operations should work after the fix."""
    from flywheel.todo import Todo

    # Test various normal cases that should still work
    cases = [
        tmp_path / "simple" / "todo.json",
        tmp_path / "nested" / "deep" / "path" / "todo.json",
        tmp_path / "a" / "b" / "c" / "d" / "e" / "todo.json",
    ]

    for db_path in cases:
        storage = TodoStorage(str(db_path))
        storage.save([Todo(id=1, text="test", done=False)])
        assert db_path.exists(), f"Should have created {db_path}"
        loaded = storage.load()
        assert len(loaded) == 1
