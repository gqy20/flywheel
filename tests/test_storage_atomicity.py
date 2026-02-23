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


def test_concurrent_directory_creation_no_file_exists_error(tmp_path) -> None:
    """Regression test for issue #5432: TOCTOU race in _ensure_parent_directory.

    Tests that save() does not raise FileExistsError when parent directory
    is created concurrently between the exists() check and mkdir() call.

    The bug: exist_ok=False in mkdir() causes FileExistsError if another
    process creates the directory after our exists() check returns False.
    The fix: use exist_ok=True since we already validated no parent is a file.
    """
    import threading

    db = tmp_path / "subdir" / "todo.json"
    barrier = threading.Barrier(3)  # Synchronize threads
    errors = []
    success_count = 0
    lock = threading.Lock()

    def save_concurrently(thread_id: int) -> None:
        """Each thread tries to save to the same new location."""
        nonlocal success_count
        try:
            storage = TodoStorage(str(db))
            barrier.wait()  # Synchronize all threads to start simultaneously
            todos = [Todo(id=thread_id, text=f"thread-{thread_id}")]
            storage.save(todos)
            with lock:
                success_count += 1
        except FileExistsError as e:
            errors.append((thread_id, f"FileExistsError: {e}"))
        except Exception as e:
            errors.append((thread_id, f"{type(e).__name__}: {e}"))

    # Start multiple threads that will all try to create the same parent directory
    threads = [threading.Thread(target=save_concurrently, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No thread should encounter FileExistsError from the TOCTOU race
    file_exists_errors = [e for e in errors if "FileExistsError" in e[1]]
    assert len(file_exists_errors) == 0, (
        f"TOCTOU race caused FileExistsError in {len(file_exists_errors)} threads: "
        f"{file_exists_errors}"
    )

    # At least one thread should have succeeded
    assert success_count >= 1, f"Expected at least 1 success, got {success_count}. Errors: {errors}"

    # Final file should be valid JSON
    storage = TodoStorage(str(db))
    loaded = storage.load()
    assert isinstance(loaded, list)
    assert len(loaded) >= 1


def test_mkdir_with_exist_ok_true_handles_concurrent_creation(tmp_path) -> None:
    """Direct test for issue #5432: mkdir should use exist_ok=True.

    Simulates TOCTOU race where directory is created between exists() check and mkdir().
    With exist_ok=False, this would raise FileExistsError.
    With exist_ok=True, the operation succeeds.

    This test verifies the fix by ensuring _ensure_parent_directory handles
    the case where the directory appears during the exists() -> mkdir() window.
    """
    from flywheel.storage import _ensure_parent_directory

    # Create a unique subdirectory path that doesn't exist yet
    db_path = tmp_path / "race_test" / "todo.json"
    parent = db_path.parent

    # Verify parent doesn't exist initially
    assert not parent.exists()

    # Track calls to exists() for the parent directory
    original_exists = Path.exists
    exists_call_count = 0
    exists_called_for_parent = False

    def exists_with_race_detection(self):
        nonlocal exists_call_count, exists_called_for_parent
        result = original_exists(self)
        if self == parent:
            exists_call_count += 1
            exists_called_for_parent = True
            # On the last exists check for parent (before mkdir), simulate race
            # First call is in the loop checking file-as-directory
            # Second call is the "if not parent.exists()" check
            # We want to intercept the second call to simulate the race
            if exists_call_count == 2:
                # Simulate TOCTOU race: directory is created by another process
                # between our check and our mkdir call
                parent.mkdir(parents=True)  # Another process creates it
                return False  # But we say it doesn't exist (race window)
        return result

    with patch.object(Path, "exists", exists_with_race_detection):
        # This should NOT raise FileExistsError with exist_ok=True
        # Without the fix (exist_ok=False), this would raise:
        # FileExistsError: [Errno 17] File exists: '...race_test'
        _ensure_parent_directory(db_path)

    # Verify the test actually exercised the race condition path
    assert exists_called_for_parent, "Test did not trigger the expected code path"
    assert exists_call_count == 2, f"Expected 2 exists calls for parent, got {exists_call_count}"

    # Verify directory exists
    assert parent.is_dir()


def test_ensure_parent_rejects_file_as_parent(tmp_path) -> None:
    """Test that _ensure_parent_directory still raises ValueError for file-as-directory."""
    from flywheel.storage import _ensure_parent_directory

    # Create a file where we need a directory
    file_path = tmp_path / "file.json"
    file_path.write_text("not a directory")

    # Try to use a path that requires file.json to be a directory
    invalid_path = file_path / "subdir" / "db.json"

    # Should raise ValueError, not silently succeed
    with pytest.raises(ValueError, match="exists as a file, not a directory"):
        _ensure_parent_directory(invalid_path)


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
