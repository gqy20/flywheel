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
        Todo(id=2, text="task with quotes: \"test\"", done=True),
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
        raise AssertionError(
            f"File was corrupted by concurrent writes. Got error: {e}"
        ) from e

    # Verify we got some valid todo data
    assert isinstance(final_todos, list), "Final data should be a list"
    # All todos should have valid structure
    for todo in final_todos:
        assert hasattr(todo, "id"), "Todo should have id"
        assert hasattr(todo, "text"), "Todo should have text"
        assert isinstance(todo.text, str), "Todo text should be a string"


# =============================================================================
# File Lock Mechanism Tests (Issue #5391)
# =============================================================================


def test_file_lock_parameter_default_false(tmp_path) -> None:
    """Test that use_locking parameter defaults to False for backward compatibility."""
    db = tmp_path / "todo.json"
    # Default should be no locking
    storage = TodoStorage(str(db))
    assert storage.use_locking is False


def test_file_lock_parameter_can_be_enabled(tmp_path) -> None:
    """Test that use_locking can be set to True."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), use_locking=True)
    assert storage.use_locking is True


def test_save_with_locking_enabled(tmp_path) -> None:
    """Test that save works correctly when file locking is enabled."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), use_locking=True)

    todos = [Todo(id=1, text="test with locking")]
    storage.save(todos)

    # Verify save worked
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test with locking"


def test_concurrent_saves_are_serialized_with_locking(tmp_path) -> None:
    """Regression test for issue #5391: File lock prevents concurrent write race conditions.

    When two processes write to the same file simultaneously with locking enabled,
    the writes should be serialized (not interleaved). Each process should complete
    its full write before the next process starts.
    """
    import multiprocessing
    import time

    db = tmp_path / "locked.json"

    def save_with_lock(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that saves todos with file locking enabled."""
        try:
            storage = TodoStorage(str(db), use_locking=True)
            # Each worker writes a distinct set of todos
            todos = [
                Todo(id=1, text=f"worker-{worker_id}-item-1"),
                Todo(id=2, text=f"worker-{worker_id}-item-2"),
                Todo(id=3, text=f"worker-{worker_id}-item-3"),
            ]
            storage.save(todos)

            # Small delay to increase race condition likelihood
            time.sleep(0.002)

            result_queue.put(("success", worker_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run workers concurrently with locking
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=save_with_lock, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=15)

    # All should succeed
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # File should contain valid JSON from exactly one worker (serialized writes)
    storage = TodoStorage(str(db), use_locking=True)
    final_todos = storage.load()

    assert len(final_todos) == 3, "Should have exactly 3 todos from one worker"

    # All todos should be from the SAME worker (no interleaving)
    worker_ids = set()
    for todo in final_todos:
        # Extract worker ID from text like "worker-2-item-1"
        parts = todo.text.split("-")
        worker_ids.add(int(parts[1]))

    assert len(worker_ids) == 1, (
        f"Expected all todos from same worker, but got from workers: {worker_ids}. "
        "This indicates writes were interleaved (locking failed)."
    )


def test_lock_released_after_exception_during_write(tmp_path) -> None:
    """Test that file lock is released even if an exception occurs during write."""
    from unittest.mock import patch

    db = tmp_path / "lock_test.json"
    storage = TodoStorage(str(db), use_locking=True)

    # Create initial data
    storage.save([Todo(id=1, text="initial")])

    # Simulate write failure during the locked operation
    import tempfile

    original_mkstemp = tempfile.mkstemp

    def failing_mkstemp(*args, **kwargs):
        raise OSError("Simulated write failure")

    with (
        patch.object(tempfile, "mkstemp", failing_mkstemp),
        pytest.raises(OSError, match="Simulated write failure"),
    ):
        storage.save([Todo(id=2, text="should fail")])

    # Lock should have been released - verify we can write again
    tempfile.mkstemp = original_mkstemp

    # This should succeed (lock was released)
    storage.save([Todo(id=3, text="after failure")])

    # Verify the file was updated
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "after failure"


def test_backward_compatibility_no_locking_by_default(tmp_path) -> None:
    """Test that default behavior (no locking) still works for backward compatibility."""
    db = tmp_path / "no_lock.json"

    # First create the file
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    # Verify it works with default (no locking)
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "initial"


def test_lock_context_manager_exists(tmp_path) -> None:
    """Test that _acquire_lock context manager exists and works."""
    db = tmp_path / "lock_cm.json"
    storage = TodoStorage(str(db), use_locking=True)

    # The context manager should exist
    assert hasattr(storage, "_acquire_lock"), "TodoStorage should have _acquire_lock method"

    # Using the context manager should not raise
    with storage._acquire_lock():
        pass  # Lock acquired and released


def test_lock_context_manager_no_locking_mode(tmp_path) -> None:
    """Test that _acquire_lock is a no-op when use_locking=False."""
    db = tmp_path / "no_lock_cm.json"
    storage = TodoStorage(str(db), use_locking=False)

    # Should be a no-op context manager
    with storage._acquire_lock():
        storage.save([Todo(id=1, text="test")])

    # Verify save worked
    loaded = storage.load()
    assert len(loaded) == 1
