"""Tests for atomic file write behavior in TodoStorage.

This test suite verifies that TodoStorage.save() writes files atomically,
preventing data corruption if the process crashes during write.
"""

from __future__ import annotations

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


def test_save_with_stale_temp_file_from_previous_crash(tmp_path) -> None:
    """Regression test for issue #1986: Cleanup stale temp files from previous crashes.

    Before fix: If a temp file from a previous crash exists, it may interfere
    with subsequent writes or clutter the directory.
    After fix: Stale temp files matching our pattern are cleaned up before write.
    """
    import tempfile

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a stale temp file as if from a previous crash
    # This simulates a temp file that was created but never renamed
    original_mkstemp = tempfile.mkstemp
    stale_temp_paths = []

    def create_stale_temp(*args, **kwargs):
        """Create temp file and track it, but don't complete the save."""
        fd, path = original_mkstemp(*args, **kwargs)
        stale_temp_paths.append(Path(path))
        # Write some content to the temp file
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write('{"stale": "data"}')
        # Return a new fd/path for the actual save
        return original_mkstemp(*args, **kwargs)

    with patch("tempfile.mkstemp", side_effect=create_stale_temp):
        # First save that will create and abandon a temp file
        storage.save([Todo(id=1, text="first")])

    # Verify stale temp file exists
    stale_temps = list(db.parent.glob(f".{db.name}.*.tmp"))
    assert len(stale_temps) > 0, "Should have stale temp files for testing"

    # Now do another save - this should clean up the stale temp files
    storage.save([Todo(id=2, text="second")])

    # After successful save, stale temp files should be cleaned up
    remaining_temps = list(db.parent.glob(f".{db.name}.*.tmp"))

    # The temp files from previous crashed writes should be removed
    # (we may still have a temp file from the current write in progress,
    # but after save completes it should be renamed or cleaned up)
    assert len(remaining_temps) == 0, (
        f"Stale temp files should be cleaned up after successful save. "
        f"Found: {remaining_temps}"
    )

    # Verify the data was written correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "second"


def test_save_with_multiple_stale_temp_files(tmp_path) -> None:
    """Regression test for issue #1986: Multiple stale temp files from crashed processes.

    Tests that if multiple processes crashed leaving various .tmp files,
    a new save cleans them all up.
    """
    db = tmp_path / "todo.json"

    # Create multiple stale temp files as if from multiple crashed processes
    stale_files = []
    for i in range(3):
        stale = db.parent / f".{db.name}.{i}.tmp"
        stale.write_text(f'{{"stale_{i}": "data"}}', encoding="utf-8")
        stale_files.append(stale)

    # Verify all stale files exist
    for f in stale_files:
        assert f.exists(), f"Stale temp file {f} should exist"

    # Now do a save - this should clean up all stale temp files
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="clean save")])

    # All stale temp files should be cleaned up
    remaining_temps = list(db.parent.glob(f".{db.name}.*.tmp"))
    assert len(remaining_temps) == 0, (
        f"All stale temp files should be cleaned up. Found: {remaining_temps}"
    )

    # Verify the data was written correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "clean save"


def test_temp_file_cleanup_on_save_failure(tmp_path) -> None:
    """Regression test for issue #1986: Temp file cleanup when os.replace fails.

    Before fix: If os.replace fails, temp file might not be cleaned up.
    After fix: Temp file is always cleaned up via try/except.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="initial")])

    # Track temp files created during save
    temp_files_created = []
    original_mkstemp = __import__("tempfile").mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    # Make os.replace fail to test cleanup
    def failing_replace(src, dst):
        raise OSError("Simulated replace failure")

    with (
        patch("tempfile.mkstemp", side_effect=tracking_mkstemp),
        patch("flywheel.storage.os.replace", side_effect=failing_replace),
        pytest.raises(OSError, match="Simulated replace failure"),
    ):
        storage.save([Todo(id=2, text="should not save")])

    # Temp file created by the failed save should be cleaned up
    # Give a small delay for cleanup to complete
    import time
    time.sleep(0.1)

    remaining_temps = [p for p in temp_files_created if p.exists()]
    assert len(remaining_temps) == 0, (
        f"Temp file should be cleaned up after failed save. Found: {remaining_temps}"
    )

    # Original data should be intact
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "initial"
