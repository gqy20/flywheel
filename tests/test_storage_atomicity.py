"""Tests for atomic file write behavior in TodoStorage.

This test suite verifies that TodoStorage.save() writes files atomically,
preventing data corruption if the process crashes during write.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_is_atomic_with_os_replace(tmp_path) -> None:
    """Test that save uses atomic os.replace instead of non-atomic write_text."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Mock os.replace to track if it was called
    with patch("flywheel.storage.os.replace") as mock_replace:
        storage.save(todos)
        # Verify atomic replace was used
        mock_replace.assert_called_once()

    # Verify file content is still valid
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "initial"


def test_write_failure_preserves_original_file(tmp_path) -> None:
    """Test that if write fails, original file remains intact."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Get the original file content
    original_content = db.read_text(encoding="utf-8")

    # Simulate write failure by making temp file write fail
    def failing_mkstemp(*args, **kwargs):
        # Fail on any temp file creation
        raise OSError("Simulated write failure")

    import tempfile

    original = tempfile.mkstemp

    with (
        patch.object(tempfile, "mkstemp", failing_mkstemp),
        pytest.raises(OSError, match="Simulated write failure"),
    ):
        storage.save([Todo(id=3, text="new")])

    # Restore original
    tempfile.mkstemp = original

    # Verify original file is unchanged
    assert db.read_text(encoding="utf-8") == original_content

    # Verify we can still load the original data
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "original"
    assert loaded[1].text == "data"


def test_temp_file_created_in_same_directory(tmp_path) -> None:
    """Test that temp file is created in same directory as target for atomic rename."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track temp file creation via mkstemp
    temp_files_created = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    import tempfile

    original = tempfile.mkstemp

    with patch.object(tempfile, "mkstemp", tracking_mkstemp):
        storage.save(todos)

    # Restore original
    tempfile.mkstemp = original

    # Verify temp file was created in same directory
    assert len(temp_files_created) >= 1
    assert temp_files_created[0].parent == db.parent
    # Temp file should start with the base filename
    assert temp_files_created[0].name.startswith(".todo.json.")


def test_atomic_write_produces_valid_json(tmp_path) -> None:
    """Test that atomic write produces valid, parseable JSON."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task with unicode: 你好"),
        Todo(id=2, text='task with quotes: "test"', done=True),
        Todo(id=3, text="task with \\n newline"),
    ]

    storage.save(todos)

    # Verify file contains valid JSON
    raw_content = db.read_text(encoding="utf-8")
    parsed = json.loads(raw_content)

    assert len(parsed) == 3
    assert parsed[0]["text"] == "task with unicode: 你好"
    assert parsed[1]["text"] == 'task with quotes: "test"'
    assert parsed[1]["done"] is True


def test_concurrent_write_safety(tmp_path) -> None:
    """Test that atomic write provides safety against concurrent writes."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initial write
    todos1 = [Todo(id=1, text="first")]
    storage.save(todos1)

    # Simulate concurrent write using same storage object
    todos2 = [Todo(id=1, text="second"), Todo(id=2, text="added")]
    storage.save(todos2)

    # Final state should be consistent
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "second"
    assert loaded[1].text == "added"


def test_concurrent_save_from_multiple_processes(tmp_path) -> None:
    """Regression test for issue #1925: Race condition in concurrent saves.

    Tests that multiple processes saving to the same file concurrently
    do not corrupt the data. Each process writes a different set of todos,
    and after all operations complete, the file should contain valid JSON
    representing one of the process writes (not corrupted data).
    """
    import multiprocessing
    import time

    db = tmp_path / "concurrent.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that saves todos and reports success."""
        try:
            storage = TodoStorage(str(db))
            # Each worker creates unique todos with worker_id in text
            todos = [
                Todo(id=i, text=f"worker-{worker_id}-todo-{i}"),
                Todo(id=i + 1, text=f"worker-{worker_id}-todo-{i + 1}"),
            ]
            storage.save(todos)

            # Small random delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 5))

            # Verify we can read back valid data
            loaded = storage.load()
            result_queue.put(("success", worker_id, len(loaded)))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded without errors
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Final verification: file should contain valid JSON
    # (not necessarily all data due to last-writer-wins, but definitely valid JSON)
    storage = TodoStorage(str(db))

    # This should not raise json.JSONDecodeError or ValueError
    try:
        final_todos = storage.load()
    except (json.JSONDecodeError, ValueError) as e:
        raise AssertionError(f"File was corrupted by concurrent writes. Got error: {e}") from e

    # Verify we got some valid todo data
    assert isinstance(final_todos, list), "Final data should be a list"
    # All todos should have valid structure
    for todo in final_todos:
        assert hasattr(todo, "id"), "Todo should have id"
        assert hasattr(todo, "text"), "Todo should have text"
        assert isinstance(todo.text, str), "Todo text should be a string"


# Tests for issue #2536: File locking for concurrent write safety
def test_concurrent_write_with_lock_prevents_data_corruption(tmp_path) -> None:
    """Regression test for issue #2536: File locking prevents race conditions.

    Tests that when multiple processes write simultaneously, they are
    serialized by file locks, preventing data corruption.
    """
    import multiprocessing

    db = tmp_path / "locked_concurrent.json"

    def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves and verifies data integrity."""
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}-data")]
            storage.save(todos)

            # Verify we can read back valid data
            storage.load()
            result_queue.put(("success", worker_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 3
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Final file should contain valid JSON
    storage = TodoStorage(str(db))
    final_todos = storage.load()
    assert isinstance(final_todos, list)


def test_lock_timeout_raises_timeout_error(tmp_path) -> None:
    """Regression test for issue #2536: Lock timeout behavior.

    Tests that when a lock cannot be acquired within timeout,
    a TimeoutError is raised with a clear message.
    """
    import multiprocessing
    import time

    db = tmp_path / "timeout_test.json"

    def hold_lock_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that holds write lock for an extended period."""
        try:
            from flywheel.storage import _file_lock

            storage = TodoStorage(str(db))
            # Hold lock manually for extended period
            with _file_lock(storage.path, exclusive=True, timeout=2.0):
                storage.save([Todo(id=1, text="holding lock")])
                # Signal we're holding the lock
                result_queue.put(("holder", "acquired"))
                # Hold the lock for a while
                time.sleep(0.5)
            result_queue.put(("holder", "released"))
        except Exception as e:
            result_queue.put(("holder_error", str(e)))

    def competing_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that attempts to acquire lock while held."""
        try:
            import time

            # Wait for holder to acquire lock
            time.sleep(0.1)
            storage = TodoStorage(str(db))
            # Set a very short timeout for testing
            storage._lock_timeout = 0.15
            storage.save([Todo(id=2, text="competing")])
            result_queue.put(("competitor", "success"))
        except TimeoutError as e:
            result_queue.put(("competitor_timeout", str(e)))
        except Exception as e:
            result_queue.put(("competitor_error", str(e)))

    # Start holder and competing processes
    result_queue = multiprocessing.Queue()
    holder = multiprocessing.Process(target=hold_lock_worker, args=(result_queue,))
    competitor = multiprocessing.Process(target=competing_worker, args=(result_queue,))

    holder.start()
    competitor.start()

    holder.join(timeout=5)
    competitor.join(timeout=5)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Verify timeout occurred
    timeout_events = [r for r in results if r[0] == "competitor_timeout"]
    # With proper locking, competitor should timeout
    assert len(timeout_events) >= 1, f"Expected lock timeout to occur, got: {results}"


def test_load_acquires_shared_lock_to_prevent_read_during_write(tmp_path) -> None:
    """Regression test for issue #2536: Load uses shared lock.

    Tests that load() acquires a shared lock to prevent reading
    while a write is in progress.
    """
    import multiprocessing

    db = tmp_path / "read_during_write.json"

    # Initialize with data
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    def write_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that performs a slow write."""
        try:
            storage = TodoStorage(str(db))
            storage._lock_timeout = 2.0
            storage.save([Todo(id=2, text="written"), Todo(id=3, text="data")])
            result_queue.put(("write", "success"))
        except Exception as e:
            result_queue.put(("write_error", str(e)))

    def read_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that reads while write may be in progress."""
        try:
            storage = TodoStorage(str(db))
            storage._lock_timeout = 2.0
            # Small delay to potentially race with write
            import time

            time.sleep(0.05)
            todos = storage.load()
            result_queue.put(("read", len(todos)))
        except Exception as e:
            result_queue.put(("read_error", str(e)))

    result_queue = multiprocessing.Queue()
    writer = multiprocessing.Process(target=write_worker, args=(result_queue,))
    reader = multiprocessing.Process(target=read_worker, args=(result_queue,))

    writer.start()
    reader.start()

    writer.join(timeout=5)
    reader.join(timeout=5)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Both should succeed without corruption errors
    write_errors = [r for r in results if r[0] == "write_error"]
    read_errors = [r for r in results if r[0] == "read_error"]
    assert len(write_errors) == 0, f"Write failed: {write_errors}"
    assert len(read_errors) == 0, f"Read failed: {read_errors}"

    # Final data should be valid
    storage = TodoStorage(str(db))
    final = storage.load()
    assert isinstance(final, list)


def test_lock_released_on_exception_during_save(tmp_path) -> None:
    """Regression test for issue #2536: Lock released on exception.

    Tests that file locks are properly released even when an
    exception occurs during save operation.
    """
    import multiprocessing

    db = tmp_path / "exception_lock.json"

    def failing_save_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that triggers an exception during save."""
        try:
            from unittest.mock import patch

            storage = TodoStorage(str(db))
            storage._lock_timeout = 2.0

            # Mock json.dumps to fail
            def failing_dumps(*args, **kwargs):
                raise ValueError("Simulated serialization failure")

            with patch("flywheel.storage.json.dumps", failing_dumps):
                storage.save([Todo(id=1, text="test")])

            result_queue.put(("save", "unexpected_success"))
        except ValueError:
            result_queue.put(("save", "expected_error"))
        except Exception as e:
            result_queue.put(("save_error", str(e)))

    def subsequent_save_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that attempts to save after exception."""
        try:
            import time

            time.sleep(0.2)  # Wait for first worker to fail
            storage = TodoStorage(str(db))
            storage._lock_timeout = 2.0
            storage.save([Todo(id=2, text="recovery")])
            result_queue.put(("recovery", "success"))
        except TimeoutError as e:
            result_queue.put(("recovery_timeout", str(e)))
        except Exception as e:
            result_queue.put(("recovery_error", str(e)))

    result_queue = multiprocessing.Queue()
    failer = multiprocessing.Process(target=failing_save_worker, args=(result_queue,))
    recovery = multiprocessing.Process(target=subsequent_save_worker, args=(result_queue,))

    failer.start()
    recovery.start()

    failer.join(timeout=5)
    recovery.join(timeout=5)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # First worker should have error, recovery should succeed (lock was released)
    recovery_results = [r for r in results if r[0].startswith("recovery")]
    assert len(recovery_results) > 0, "Recovery worker should have completed"
    # Recovery should NOT timeout (lock was properly released)
    recovery_timeouts = [r for r in recovery_results if r[0] == "recovery_timeout"]
    assert len(recovery_timeouts) == 0, "Lock should have been released after exception"
