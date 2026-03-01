"""Regression tests for issue #6590: TOCTOU race condition in _ensure_parent_directory.

Issue: The exist_ok=False parameter combined with a preceding parent.exists() check
creates a Time-of-Check to Time-of-Use (TOCTOU) race condition. If another process
creates the parent directory between the check and mkdir, a FileExistsError is raised.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_concurrent_directory_creation_no_exception(tmp_path) -> None:
    """Issue #6590: Concurrent calls to _ensure_parent_directory should not raise.

    When multiple threads/processes try to create the same parent directory
    concurrently, none should fail with FileExistsError.
    """
    results_queue = multiprocessing.Queue()

    def ensure_dir_worker(worker_id: int, shared_path: Path) -> None:
        """Worker that tries to ensure parent directory exists."""
        try:
            # Each worker targets the same directory path
            target_file = shared_path / "subdir" / f"file_{worker_id}.json"
            _ensure_parent_directory(target_file)
            results_queue.put(("success", worker_id))
        except FileExistsError as e:
            # This is the bug we're testing for
            results_queue.put(("file_exists_error", worker_id, str(e)))
        except Exception as e:
            results_queue.put(("error", worker_id, str(e)))

    # Shared parent directory path that all workers will try to create
    shared_path = tmp_path / "shared_dir"

    # Run multiple workers that all try to create the same parent directory
    num_workers = 10
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=ensure_dir_worker,
            args=(i, shared_path)
        )
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())

    successes = [r for r in results if r[0] == "success"]
    file_exists_errors = [r for r in results if r[0] == "file_exists_error"]
    other_errors = [r for r in results if r[0] == "error"]

    # No worker should get FileExistsError (this is the bug being fixed)
    assert len(file_exists_errors) == 0, (
        f"TOCTOU race condition detected! {len(file_exists_errors)} workers "
        f"got FileExistsError: {file_exists_errors}"
    )

    # All workers should succeed
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}. "
        f"Errors: {other_errors}"
    )


def test_concurrent_save_to_new_shared_directory_no_exception(tmp_path) -> None:
    """Issue #6590: Multiple processes saving to new shared directory should work.

    This is a higher-level integration test that verifies the fix works
    through the TodoStorage.save() method, which calls _ensure_parent_directory.
    """
    results_queue = multiprocessing.Queue()

    def save_worker(worker_id: int, shared_dir: Path) -> None:
        """Worker that saves a todo to a new path in shared directory."""
        try:
            # Each worker saves to a different file, but all in the same new directory
            db_path = shared_dir / f"todo_{worker_id}.json"
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=1, text=f"worker-{worker_id} todo")]
            storage.save(todos)
            results_queue.put(("success", worker_id))
        except FileExistsError as e:
            # This is the bug we're testing for
            results_queue.put(("file_exists_error", worker_id, str(e)))
        except Exception as e:
            results_queue.put(("error", worker_id, str(e)))

    # Shared directory that doesn't exist yet
    shared_dir = tmp_path / "new_shared_dir"

    # Run multiple workers that all need the same parent directory created
    num_workers = 8
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=save_worker,
            args=(i, shared_dir)
        )
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())

    successes = [r for r in results if r[0] == "success"]
    file_exists_errors = [r for r in results if r[0] == "file_exists_error"]
    other_errors = [r for r in results if r[0] == "error"]

    # No worker should get FileExistsError
    assert len(file_exists_errors) == 0, (
        f"TOCTOU race condition detected! {len(file_exists_errors)} workers "
        f"got FileExistsError: {file_exists_errors}"
    )

    # All workers should succeed
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}. "
        f"Errors: {other_errors}"
    )


def test_single_process_behavior_unchanged(tmp_path) -> None:
    """Issue #6590: Verify single-process behavior remains unchanged after fix.

    The fix should not change the behavior for single-process use cases:
    - Directory creation should still work when parent doesn't exist
    - No errors should be raised for normal operations
    """
    # Test 1: Create new nested directory
    db_path = tmp_path / "level1" / "level2" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Should work without errors
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify directory was created
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"

    # Test 2: Save again when directory already exists
    todos2 = [Todo(id=1, text="updated")]
    storage.save(todos2)

    loaded2 = storage.load()
    assert loaded2[0].text == "updated"
