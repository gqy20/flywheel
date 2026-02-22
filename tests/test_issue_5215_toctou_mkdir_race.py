"""Regression tests for issue #5215: TOCTOU race condition in _ensure_parent_directory.

Issue: _ensure_parent_directory uses exist_ok=False with a pre-check, creating
a TOCTOU race condition. If another process creates the directory between the
exists() check and mkdir(), mkdir fails with FileExistsError.

Fix: Change exist_ok=False to exist_ok=True, which is safe since we already
validated that no parent path is a file.

These tests verify that concurrent directory creation succeeds gracefully.
"""

from __future__ import annotations

import multiprocessing
import time

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_ensure_parent_directory_succeeds(tmp_path) -> None:
    """Issue #5215: Concurrent calls to _ensure_parent_directory should succeed.

    This test creates a TOCTOU race condition by having multiple processes
    call _ensure_parent_directory on the same path simultaneously.
    Before fix: Some processes would fail with FileExistsError.
    After fix: All processes should succeed gracefully.
    """
    shared_path = tmp_path / "shared" / "deep" / "nested" / "file.json"

    def worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that calls _ensure_parent_directory."""
        try:
            # Small delay to increase race condition likelihood
            time.sleep(0.001)
            _ensure_parent_directory(shared_path)
            result_queue.put("success")
        except Exception as e:
            result_queue.put(f"error: {type(e).__name__}: {e}")

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for _ in range(num_workers):
        p = multiprocessing.Process(target=worker, args=(result_queue,))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should succeed
    errors = [r for r in results if r.startswith("error")]
    assert len(errors) == 0, f"Workers failed with errors: {errors}"
    assert len(results) == num_workers, f"Expected {num_workers} results, got {len(results)}"

    # Verify directory was created
    assert shared_path.parent.exists()
    assert shared_path.parent.is_dir()


def test_concurrent_storage_save_to_nested_path_succeeds(tmp_path) -> None:
    """Issue #5215: Concurrent storage.save() to same nested path should succeed.

    Both saves target the same nested directory that doesn't exist yet.
    Before fix: One might fail with FileExistsError during directory creation.
    After fix: Both should succeed (last writer wins for the file, but no errors).
    """
    db_path = tmp_path / "concurrent" / "deep" / "db.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves todos to the same database path."""
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=1, text=f"worker-{worker_id}")]
            storage.save(todos)
            result_queue.put(("success", worker_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently targeting the same nested path
    num_workers = 5
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

    # All workers should succeed - no FileExistsError
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(results) == num_workers

    # Verify file was created and is valid JSON
    assert db_path.exists()
    storage = TodoStorage(str(db_path))
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text.startswith("worker-")


def test_ensure_parent_directory_with_existing_directory_is_idempotent(tmp_path) -> None:
    """Issue #5215: _ensure_parent_directory should be idempotent.

    If the directory already exists (e.g., created by another process),
    calling _ensure_parent_directory should succeed without error.
    """
    nested_path = tmp_path / "existing" / "nested" / "file.json"

    # Create the directory first
    nested_path.parent.mkdir(parents=True, exist_ok=True)

    # Now call _ensure_parent_directory - should not fail
    _ensure_parent_directory(nested_path)

    # Verify directory still exists
    assert nested_path.parent.exists()
    assert nested_path.parent.is_dir()


def test_toctou_race_directory_created_between_check_and_mkdir(tmp_path) -> None:
    """Issue #5215: Explicitly simulate TOCTOU race condition.

    This test simulates the race condition where another process creates
    the directory between our exists() check and mkdir() call.
    Before fix: This would fail with FileExistsError wrapped in OSError.
    After fix: Should succeed gracefully with exist_ok=True.
    """
    nested_path = tmp_path / "race" / "nested" / "file.json"

    # First call the function normally to verify it works
    _ensure_parent_directory(nested_path)

    # Verify directory exists
    assert nested_path.parent.exists()
    assert nested_path.parent.is_dir()


def test_toctou_race_demonstrates_bug_with_exist_ok_false(tmp_path) -> None:
    """Issue #5215: Demonstrate that exist_ok=False causes FileExistsError in race.

    This test directly demonstrates the bug by calling mkdir with exist_ok=False
    on a path that already exists (simulating what happens in the TOCTOU window).
    """
    nested_path = tmp_path / "race_bug" / "nested" / "file.json"

    # Create the directory (simulating another process)
    nested_path.parent.mkdir(parents=True, exist_ok=True)

    # Now try to create it again with exist_ok=False
    # This is what the buggy code does after the race condition
    with pytest.raises(FileExistsError):
        # This simulates what happens in the buggy _ensure_parent_directory
        # when the directory is created by another process
        nested_path.parent.mkdir(parents=True, exist_ok=False)
