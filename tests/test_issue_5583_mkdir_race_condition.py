"""Regression tests for issue #5583: Race condition in _ensure_parent_directory.

Issue: exist_ok=False in mkdir() can raise FileExistsError if directory is
created concurrently between the exists() check and mkdir() call.

These tests verify that concurrent directory creation doesn't cause failures.
"""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
from unittest import mock

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory


def test_mkdir_race_condition_exist_ok_false_vs_true(tmp_path) -> None:
    """Issue #5583: Demonstrate race condition with exist_ok=False vs True.

    This test shows that:
    1. exist_ok=False can raise FileExistsError when directory is created concurrently
    2. exist_ok=True handles this race condition gracefully
    """
    parent_dir = tmp_path / "race_test_dir"

    # Test 1: Show that exist_ok=False can fail when directory exists
    # First create the directory
    parent_dir.mkdir(parents=True, exist_ok=True)

    # Now try to create it again with exist_ok=False - this should raise
    with pytest.raises(FileExistsError):
        parent_dir.mkdir(parents=True, exist_ok=False)

    # Test 2: Show that exist_ok=True handles existing directory gracefully
    parent_dir2 = tmp_path / "race_test_dir2"
    parent_dir2.mkdir(parents=True, exist_ok=True)
    # This should NOT raise - exist_ok=True handles the race
    parent_dir2.mkdir(parents=True, exist_ok=True)  # No exception


def test_ensure_parent_directory_with_race_condition_simulation(tmp_path) -> None:
    """Issue #5583: _ensure_parent_directory should handle race conditions.

    This test directly simulates what happens when another process creates
    the directory between the exists() check and mkdir() call.

    BEFORE FIX: This test fails because exist_ok=False raises FileExistsError
    AFTER FIX: This test passes because exist_ok=True handles the race
    """
    parent_dir = tmp_path / "simulated_race_dir"
    file_path = parent_dir / "todo.json"

    # Simulate race condition: mock mkdir to first create the directory
    # then call the original mkdir (which will find it already exists)
    original_mkdir = Path.mkdir
    call_count = [0]

    def mock_mkdir(self, *args, **kwargs):
        call_count[0] += 1
        if self == parent_dir and call_count[0] == 1:
            # Simulate another process creating the directory right before our mkdir
            original_mkdir(self, parents=True, exist_ok=True)
        # Now call the actual mkdir with exist_ok from kwargs
        return original_mkdir(self, *args, **kwargs)

    with mock.patch.object(Path, "mkdir", mock_mkdir):
        # With exist_ok=True (the fix), this should succeed
        # No FileExistsError should be raised
        _ensure_parent_directory(file_path)

    # Verify directory exists
    assert parent_dir.exists()


def test_concurrent_save_creates_directory_safely(tmp_path) -> None:
    """Issue #5583: Concurrent saves should not raise FileExistsError.

    Race condition: If two processes call save() concurrently and both try
    to create the parent directory, exist_ok=False would cause FileExistsError
    for one of them.

    With the fix (exist_ok=True), both should succeed.
    """
    # Create a path in a subdirectory that doesn't exist yet
    db_path = tmp_path / "subdir1" / "subdir2" / "todo.json"

    errors = []

    def save_todos(storage, todos):
        try:
            storage.save(todos)
            return None
        except Exception as e:
            return e

    # Run saves concurrently from multiple threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(10):
            storage = TodoStorage(str(db_path))
            future = executor.submit(save_todos, storage, [{"id": i, "text": f"todo {i}"}])
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            error = future.result()
            if error:
                errors.append(error)

    # No FileExistsError should have been raised
    file_exists_errors = [e for e in errors if isinstance(e, FileExistsError)]
    assert len(file_exists_errors) == 0, f"Race condition caused FileExistsError: {file_exists_errors}"


def test_concurrent_save_different_files_same_directory(tmp_path) -> None:
    """Issue #5583: Concurrent saves to different files in same new directory.

    This is an even more likely race condition scenario - multiple processes
    creating files in the same new directory concurrently.
    """
    errors = []

    def save_to_path(db_path, todo_id):
        try:
            storage = TodoStorage(str(db_path))
            storage.save([{"id": todo_id, "text": f"todo {todo_id}"}])
            return None
        except Exception as e:
            return e

    # All paths share the same new parent directory
    base_dir = tmp_path / "shared_new_dir"

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(10):
            db_path = base_dir / f"todo_{i}.json"
            future = executor.submit(save_to_path, db_path, i)
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            error = future.result()
            if error:
                errors.append(error)

    # No FileExistsError should have been raised
    file_exists_errors = [e for e in errors if isinstance(e, FileExistsError)]
    assert len(file_exists_errors) == 0, f"Race condition caused FileExistsError: {file_exists_errors}"


def test_file_as_directory_validation_still_works(tmp_path) -> None:
    """Issue #5583: exist_ok=True should not break file-as-directory validation.

    The fix changes exist_ok=False to exist_ok=True, but we must still
    reject paths where a parent component is a file, not a directory.
    """
    # Create a file where a directory would be needed
    blocking_file = tmp_path / "blocking.json"
    blocking_file.write_text("I am a file")

    # Try to create a database path that requires the file to be a directory
    db_path = blocking_file / "data.json"
    storage = TodoStorage(str(db_path))

    # Should still raise ValueError for file-as-directory confusion
    with pytest.raises(ValueError, match=r"(file|not a directory|path)"):
        storage.save([{"id": 1, "text": "test"}])
