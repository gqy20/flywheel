"""Tests for atomic file write behavior in TodoStorage.

This test suite verifies that TodoStorage.save() writes files atomically,
preventing data corruption if the process crashes during write.
"""

from __future__ import annotations

import contextlib
import json
import os
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


def test_partial_write_failure_preserves_original_file(tmp_path) -> None:
    """Regression test for issue #5141: Partial write failure should not corrupt file.

    If f.write() fails mid-stream (e.g., disk full), the temp file should be
    cleaned up and the original file should remain unchanged. The issue was that
    without explicit flush(), buffered writes might succeed but actual disk write
    fails, leading to a truncated temp file being renamed over the original.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="original content that should be preserved")]
    storage.save(original_todos)
    original_content = db.read_text(encoding="utf-8")

    # Create a write function that simulates partial write failure
    # by raising OSError after some bytes are written
    write_call_count = 0

    def failing_write(self, s):
        nonlocal write_call_count
        write_call_count += 1
        # Simulate disk full error on the write call
        raise OSError(28, "No space left on device")

    original_fdopen = os.fdopen

    def patched_fdopen(fd, *args, **kwargs):
        file_obj = original_fdopen(fd, *args, **kwargs)
        # Patch the write method to simulate failure
        file_obj.write = failing_write.__get__(file_obj, type(file_obj))
        return file_obj

    with (
        patch("flywheel.storage.os.fdopen", patched_fdopen),
        pytest.raises(OSError, match="No space left on device"),
    ):
        storage.save([Todo(id=2, text="this should not be saved")])

    # Verify original file is unchanged
    assert db.read_text(encoding="utf-8") == original_content

    # Verify we can still load original data
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "original content that should be preserved"


def test_flush_failure_before_replace_preserves_original_file(tmp_path) -> None:
    """Regression test for issue #5141: Flush failure should prevent rename.

    If f.flush() fails (e.g., disk full after buffered write), os.replace()
    should NOT be called. The fix adds explicit flush() before replace to catch
    disk errors before the atomic rename.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="original content")]
    storage.save(original_todos)
    original_content = db.read_text(encoding="utf-8")

    # Track whether os.replace was called
    replace_called = False
    original_replace = os.replace

    def tracking_replace(*args, **kwargs):
        nonlocal replace_called
        replace_called = True
        return original_replace(*args, **kwargs)

    # Create file objects where write succeeds but flush fails
    original_fdopen = os.fdopen

    class FailingFlushFile:
        """A file-like object where flush() fails to simulate disk full."""

        def __init__(self, real_file):
            self._real_file = real_file
            self._flush_count = 0

        def write(self, s):
            # Write succeeds (data goes to buffer)
            return self._real_file.write(s)

        def flush(self):
            self._flush_count += 1
            # First flush (explicit flush after write) fails
            # This simulates disk full after buffered write
            if self._flush_count == 1:
                raise OSError(28, "No space left on device")
            # Subsequent flushes (e.g., on close) can succeed or fail
            # We don't care - the error should already be raised

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Don't flush on close if we already have an exception
            if exc_type is None:
                with contextlib.suppress(OSError):
                    self.flush()
            return False

        def close(self):
            with contextlib.suppress(OSError):
                self.flush()
            self._real_file.close()

    def patched_fdopen(fd, *args, **kwargs):
        real_file = original_fdopen(fd, *args, **kwargs)
        return FailingFlushFile(real_file)

    with (
        patch("flywheel.storage.os.fdopen", patched_fdopen),
        patch("flywheel.storage.os.replace", tracking_replace),
        pytest.raises(OSError, match="No space left on device"),
    ):
        storage.save([Todo(id=2, text="new data")])

    # CRITICAL: os.replace should NOT have been called
    # If it was, that's the bug - we renamed a truncated file
    assert not replace_called, (
        "BUG: os.replace() was called even though flush failed! "
        "This would rename a truncated temp file over the original."
    )

    # Verify original file is unchanged
    assert db.read_text(encoding="utf-8") == original_content


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
