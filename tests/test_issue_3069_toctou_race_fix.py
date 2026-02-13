"""Regression tests for issue #3069: TOCTOU race condition in _ensure_parent_directory().

Issue: _ensure_parent_directory() has a race condition between exists() check and mkdir().
Another process could create the directory between the check and the mkdir() call,
causing FileExistsError with exist_ok=False.

These tests verify that the fix (using exist_ok=True) handles this correctly.
"""

from __future__ import annotations

import multiprocessing

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_is_idempotent(tmp_path) -> None:
    """Issue #3069: _ensure_parent_directory should be safe to call multiple times.

    With exist_ok=True, calling the function when directory already exists should
    be a no-op, not raise FileExistsError.
    """
    db_path = tmp_path / "idempotent" / "todo.json"

    # First call - directory doesn't exist
    _ensure_parent_directory(db_path)
    assert db_path.parent.exists()

    # Second call - directory now exists
    # With exist_ok=True, this should be a no-op (not raise FileExistsError)
    _ensure_parent_directory(db_path)
    assert db_path.parent.exists()

    # Third call for good measure
    _ensure_parent_directory(db_path)
    assert db_path.parent.exists()


def test_ensure_parent_directory_when_directory_created_between_check_and_mkdir(tmp_path) -> None:
    """Issue #3069: Test the TOCTOU race condition by pre-creating the directory.

    This test simulates the race by pre-creating the directory that would have
    been created by the function. With exist_ok=True, the function should still succeed.
    """
    db_path = tmp_path / "race" / "test" / "todo.json"

    # Pre-create the parent directory (simulating another process winning the race)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Now call _ensure_parent_directory - it should detect the directory exists
    # and not fail with FileExistsError
    _ensure_parent_directory(db_path)

    # Directory should still exist
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_concurrent_save_creates_parent_directory_safely(tmp_path) -> None:
    """Issue #3069: Multiple processes saving to same new parent directory should all succeed.

    This is a realistic test that simulates the actual use case:
    multiple workers trying to save to a path where the parent doesn't exist yet.
    With exist_ok=True, all workers should succeed without FileExistsError.
    """
    db = tmp_path / "shared" / "concurrent.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves todos to a path with non-existent parent."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=1, text=f"worker-{worker_id}")]
            storage.save(todos)
            result_queue.put(("success", worker_id))
        except FileExistsError as e:
            # This is the bug - race condition causes FileExistsError
            result_queue.put(("race_error", worker_id, str(e)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently, all trying to create same parent
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        # Start all at once to maximize race condition likelihood
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    race_errors = [r for r in results if r[0] == "race_error"]
    other_errors = [r for r in results if r[0] == "error"]

    # No race condition errors should occur
    assert len(race_errors) == 0, (
        f"Race condition detected: {len(race_errors)} workers hit FileExistsError. "
        f"This indicates TOCTOU race in _ensure_parent_directory(). Details: {race_errors}"
    )

    # All workers should succeed
    assert len(other_errors) == 0, f"Workers encountered errors: {other_errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Final verification: directory and file should exist
    assert db.parent.exists(), "Parent directory should exist"
    assert db.exists(), "Database file should exist"


def test_ensure_parent_directory_with_existing_directory(tmp_path) -> None:
    """Issue #3069: Should still work correctly when directory already exists."""
    db_path = tmp_path / "existing" / "todo.json"

    # Create the directory first
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # This should not raise any error
    _ensure_parent_directory(db_path)

    # Directory should still exist
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_storage_save_creates_missing_parent_directory(tmp_path) -> None:
    """Issue #3069: TodoStorage.save should create parent directory when missing."""
    # Use a path where parent doesn't exist
    db = tmp_path / "brand_new" / "nested" / "todo.json"

    assert not db.parent.exists(), "Parent should not exist initially"

    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]

    # This should work and create the parent directory
    storage.save(todos)

    # Verify parent was created
    assert db.parent.exists(), "Parent directory should be created"
    assert db.exists(), "Database file should be created"

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_storage_save_when_parent_created_by_another_process(tmp_path) -> None:
    """Issue #3069: TodoStorage.save should work when parent is created by another process.

    This simulates the race condition where another process creates the parent
    directory after TodoStorage.save() starts but before it tries to create it.
    """
    db = tmp_path / "race" / "test" / "todo.json"

    # Pre-create the parent directory (simulating race winner)
    db.parent.mkdir(parents=True, exist_ok=True)

    # Now try to save - should succeed without FileExistsError
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test")]

    storage.save(todos)

    # Verify data was saved
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"
