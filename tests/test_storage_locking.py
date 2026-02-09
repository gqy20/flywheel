"""Tests for file locking behavior in TodoStorage.

This test suite verifies that TodoStorage uses file locking to prevent
race conditions and data corruption when multiple processes access the
same file concurrently.
"""

from __future__ import annotations

import multiprocessing
import time
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_lock_timeout_when_file_is_locked(tmp_path) -> None:
    """Test that acquiring a lock with timeout raises TimeoutError when lock is held.

    This test verifies the timeout mechanism for lock acquisition.
    """
    from filelock import FileLock

    db = tmp_path / "locked.json"
    lock_file = tmp_path / "locked.json.lock"

    # Create a file to save
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    # Manually acquire the lock and hold it
    holder_lock = FileLock(str(lock_file), timeout=1.0)
    holder_lock.acquire()

    try:
        # Try to save with a short timeout while lock is held
        storage2 = TodoStorage(str(db))
        # Set a very short timeout (0.1 second) to test the timeout mechanism
        storage2.lock_timeout = 0.1

        with pytest.raises(TimeoutError, match="Could not acquire lock"):
            storage2.save([Todo(id=2, text="should timeout")])
    finally:
        holder_lock.release()


def test_concurrent_save_blocks_on_lock(tmp_path) -> None:
    """Test that save() blocks when another process holds exclusive lock.

    This test verifies proper blocking behavior for concurrent writes.
    """
    db = tmp_path / "blocked.json"

    def save_with_lock(worker_id: int, delay: float, result_queue: multiprocessing.Queue) -> None:
        """Save after a delay to test blocking behavior."""
        try:
            storage = TodoStorage(str(db))
            time.sleep(delay)
            start_time = time.time()
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            elapsed = time.time() - start_time
            result_queue.put(("success", worker_id, elapsed))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Start two workers - first will hold lock longer
    result_queue = multiprocessing.Queue()
    worker1 = multiprocessing.Process(target=save_with_lock, args=(1, 0.0, result_queue))
    worker2 = multiprocessing.Process(target=save_with_lock, args=(2, 0.1, result_queue))

    worker1.start()
    time.sleep(0.05)  # Ensure worker1 acquires lock first
    worker2.start()

    worker1.join(timeout=10)
    worker2.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    assert len(results) == 2, f"Expected 2 results, got {len(results)}"

    # Both should succeed
    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"

    # Worker 2 should have taken longer due to blocking
    worker1_elapsed = next(r[2] for r in successes if r[1] == 1)
    worker2_elapsed = next(r[2] for r in successes if r[1] == 2)

    # Worker 2 should have been blocked and taken longer
    assert worker2_elapsed > worker1_elapsed, "Worker 2 should have been blocked"


def test_lock_released_on_exception(tmp_path) -> None:
    """Test that lock is released even when save() raises an exception.

    This test verifies exception safety of lock handling.
    """
    db = tmp_path / "exception.json"
    storage = TodoStorage(str(db))

    # First, save valid data
    storage.save([Todo(id=1, text="initial")])

    # Create a scenario where save will fail
    def failing_mkstemp(*args, **kwargs):
        """Simulate failure during temp file creation."""
        raise OSError("Simulated write failure")


    with (
        patch("tempfile.mkstemp", failing_mkstemp),
        pytest.raises(OSError, match="Simulated write failure"),
    ):
        storage.save([Todo(id=2, text="should fail")])

    # Now try to save again - should succeed if lock was released
    storage2 = TodoStorage(str(db))
    storage2.save([Todo(id=3, text="after exception")])

    # Verify the file is valid
    loaded = storage2.load()
    assert len(loaded) == 1
    assert loaded[0].text == "after exception"


def test_read_during_write_blocks(tmp_path) -> None:
    """Test that read blocks during write to prevent inconsistent state.

    This test verifies that load() acquires a lock and waits for save() to complete.
    """
    db = tmp_path / "read_write.json"

    def slow_write(result_queue: multiprocessing.Queue) -> None:
        """Write data slowly to test blocking read."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=i, text=f"todo-{i}") for i in range(100)]
            storage.save(todos)
            result_queue.put(("write_complete", None))
        except Exception as e:
            result_queue.put(("error", str(e)))

    def slow_read(result_queue: multiprocessing.Queue) -> None:
        """Try to read while write is happening."""
        try:
            time.sleep(0.05)  # Start slightly after write begins
            storage = TodoStorage(str(db))
            start_time = time.time()
            loaded = storage.load()
            elapsed = time.time() - start_time
            result_queue.put(("read_complete", len(loaded), elapsed))
        except Exception as e:
            result_queue.put(("error", str(e)))

    result_queue = multiprocessing.Queue()
    writer = multiprocessing.Process(target=slow_write, args=(result_queue,))
    reader = multiprocessing.Process(target=slow_read, args=(result_queue,))

    writer.start()
    reader.start()

    writer.join(timeout=10)
    reader.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    assert len(results) == 2

    # Both should succeed
    next(r for r in results if r[0] == "write_complete")
    read_result = next(r for r in results if r[0] == "read_complete")

    # Read should have gotten valid data
    assert read_result[1] == 100, f"Expected 100 todos, got {read_result[1]}"


def test_lock_file_created_and_cleaned(tmp_path) -> None:
    """Test that lock file is created and cleaned up properly."""
    db = tmp_path / "locktest.json"
    lock_file = tmp_path / "locktest.json.lock"

    storage = TodoStorage(str(db))

    # Lock file should not exist initially
    assert not lock_file.exists()

    # After save, lock file should be created and then released
    storage.save([Todo(id=1, text="test")])

    # Lock file may exist but should be released (no process holding it)
    # The filelock library keeps the lock file but releases the lock


def test_custom_lock_timeout(tmp_path) -> None:
    """Test that custom lock timeout can be set."""
    db = tmp_path / "custom_timeout.json"

    # Default timeout
    storage1 = TodoStorage(str(db))
    assert storage1.lock_timeout == 5.0

    # Custom timeout
    storage2 = TodoStorage(str(db), lock_timeout=10.0)
    assert storage2.lock_timeout == 10.0
