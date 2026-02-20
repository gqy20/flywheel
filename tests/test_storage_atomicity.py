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


def test_toctou_race_in_directory_creation(tmp_path) -> None:
    """Regression test for issue #4664: TOCTOU race in _ensure_parent_directory.

    Tests that _ensure_parent_directory handles the TOCTOU race condition where
    another process creates the directory between our exists() check and mkdir().

    Before fix: exist_ok=False would raise FileExistsError
    After fix: exist_ok=True succeeds even if directory now exists
    """
    from unittest.mock import patch

    from flywheel.storage import _ensure_parent_directory

    # Path in a non-existent subdirectory
    subdir = tmp_path / "new_subdir"
    file_path = subdir / "todo.json"

    # Track the original mkdir method
    original_mkdir = type(subdir).mkdir
    mkdir_calls = []

    def race_mkdir(self, *args, **kwargs):
        """Mock mkdir that simulates another process creating the dir first."""
        mkdir_calls.append((args, kwargs))

        # Simulate: another process creates directory between our exists() check and mkdir()
        if kwargs.get("exist_ok") is False and not self.exists():
            # Create the directory before our mkdir call
            original_mkdir(self, parents=True, exist_ok=True)
            # Now our mkdir call will fail with FileExistsError if exist_ok=False
            # but succeed if exist_ok=True

        return original_mkdir(self, *args, **kwargs)

    with patch.object(type(subdir), "mkdir", race_mkdir):
        # With the fix (exist_ok=True), this should NOT raise FileExistsError
        _ensure_parent_directory(file_path)

    # Verify the directory was created
    assert subdir.exists(), "Parent directory should exist"
    assert len(mkdir_calls) == 1, "mkdir should have been called once"


def test_concurrent_directory_creation_no_race(tmp_path) -> None:
    """Regression test for issue #4664: Concurrent saves to new path should not race.

    Tests that multiple threads saving to the same NEW path (requiring directory
    creation) do not fail with FileExistsError due to TOCTOU race condition.
    """
    import threading

    # Use a path in a subdirectory that doesn't exist yet
    subdir = tmp_path / "new_subdir"
    db = subdir / "todo.json"

    errors = []
    success_count = 0
    lock = threading.Lock()

    def save_worker(worker_id: int) -> None:
        """Worker that saves todos, triggering directory creation."""
        nonlocal success_count
        try:
            storage = TodoStorage(str(db))
            todos = [Todo(id=worker_id, text=f"worker-{worker_id}")]
            storage.save(todos)
            with lock:
                success_count += 1
        except FileExistsError as e:
            # This is the bug we're testing for - should NOT happen
            errors.append(f"Worker {worker_id} got FileExistsError: {e}")
        except Exception as e:
            errors.append(f"Worker {worker_id} got unexpected error: {e}")

    # Create multiple threads that all try to save at the same time
    num_threads = 20
    threads = []

    # Use a barrier to maximize race condition likelihood
    barrier = threading.Barrier(num_threads)

    def barrier_save_worker(worker_id: int) -> None:
        barrier.wait()  # All threads wait here until ready
        save_worker(worker_id)

    for i in range(num_threads):
        t = threading.Thread(target=barrier_save_worker, args=(i,))
        threads.append(t)

    # Start all threads at once
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=10)

    # Verify no FileExistsError occurred
    assert len(errors) == 0, f"Race condition detected - errors: {errors}"

    # At least some threads should have succeeded
    assert success_count > 0, "No threads succeeded in saving"

    # Final file should be valid JSON
    storage = TodoStorage(str(db))
    final_todos = storage.load()
    assert len(final_todos) >= 1, "Should have at least one todo saved"


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
