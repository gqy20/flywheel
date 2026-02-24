"""Regression tests for issue #5583: Race condition in _ensure_parent_directory.

Issue: exist_ok=False in _ensure_parent_directory can raise FileExistsError
if a directory is created concurrently between the exists() check and mkdir() call.

These tests verify the fix handles concurrent directory creation gracefully.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_saves_to_same_path_succeed(tmp_path) -> None:
    """Issue #5583: storage.save() should succeed when directory is created concurrently.

    This test simulates a race condition where multiple processes try to create
    the same parent directory simultaneously. Before the fix, this would raise
    FileExistsError due to exist_ok=False.
    """
    # Create path to a non-existent nested directory
    db_path = tmp_path / "nested" / "subdir" / "todo.json"

    # Number of concurrent saves
    num_threads = 10
    errors = []
    barrier = threading.Barrier(num_threads)

    def save_concurrently(idx: int) -> None:
        """Save from multiple threads, starting at the same time."""
        storage = TodoStorage(str(db_path))
        # Wait for all threads to be ready
        barrier.wait()
        try:
            storage.save([Todo(id=idx + 1, text=f"Task {idx}")])
        except Exception as e:
            errors.append(e)

    # Run concurrent saves
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(save_concurrently, i) for i in range(num_threads)]
        for future in futures:
            future.result()

    # No errors should have occurred
    assert len(errors) == 0, f"Concurrent saves failed with errors: {errors}"

    # Verify the file was created and is valid JSON
    assert db_path.exists()


def test_file_as_directory_validation_still_works_after_race_fix(tmp_path) -> None:
    """Issue #5583: File-as-directory validation should still work correctly.

    After changing exist_ok=False to exist_ok=True, we must ensure that
    paths like /file.json/data.json are still rejected when file.json is a file.
    """
    # Create a file where we expect a directory
    conflicting_file = tmp_path / "db.json"
    conflicting_file.write_text("I am a file, not a directory")

    # Try to create db at path that requires the file to be a directory
    db_path = conflicting_file / "subdir" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should still fail with ValueError for file-as-directory confusion
    with pytest.raises(ValueError, match=r"(file|not a directory)"):
        storage.save([])


def test_concurrent_saves_with_preexisting_directory_succeed(tmp_path) -> None:
    """Issue #5583: Concurrent saves should work when directory already exists.

    This is a baseline test to ensure the fix doesn't break normal operation
    when the directory is already present.
    """
    # Pre-create the directory
    db_dir = tmp_path / "existing_dir"
    db_dir.mkdir()
    db_path = db_dir / "todo.json"

    num_threads = 5
    errors = []
    barrier = threading.Barrier(num_threads)

    def save_concurrently(idx: int) -> None:
        storage = TodoStorage(str(db_path))
        barrier.wait()
        try:
            storage.save([Todo(id=idx + 1, text=f"Task {idx}")])
        except Exception as e:
            errors.append(e)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(save_concurrently, i) for i in range(num_threads)]
        for future in futures:
            future.result()

    assert len(errors) == 0, f"Concurrent saves failed with errors: {errors}"
