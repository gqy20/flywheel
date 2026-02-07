"""Tests for atomic file write behavior in TodoStorage.

This test suite verifies that TodoStorage.save() writes files atomically,
preventing data corruption if the process crashes during write.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo

if TYPE_CHECKING:
    import multiprocessing


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
    original_write_text = Path.write_text

    def failing_write_text(self, content, encoding="utf-8", **kwargs):
        # Only fail on temp files, allow initial setup to succeed
        if self.name.startswith(".todo.json") and self.name.endswith(".tmp"):
            raise OSError("Simulated write failure")
        return original_write_text(self, content, encoding=encoding, **kwargs)

    with (
        patch.object(Path, "write_text", failing_write_text),
        pytest.raises(OSError, match="Simulated write failure"),
    ):
        storage.save([Todo(id=3, text="new")])

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

    # Track temp file creation
    temp_files_created = []
    original_write_text = Path.write_text

    def tracking_write_text(self, content, encoding="utf-8"):
        if self.name.startswith(".todo.json") and self.name.endswith(".tmp"):
            temp_files_created.append(self)
        return original_write_text(self, content, encoding=encoding)

    with patch.object(Path, "write_text", tracking_write_text):
        storage.save(todos)

    # Verify temp file was created in same directory
    assert len(temp_files_created) >= 1
    assert temp_files_created[0].parent == db.parent
    assert temp_files_created[0].name.startswith(".todo.json")


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


# REGRESSION TESTS FOR ISSUE #1986


def test_temp_filename_includes_unique_component(tmp_path) -> None:
    """Test that temp filename includes process-unique component (PID) to avoid collisions."""
    import os

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    temp_files_created = []
    original_write_text = Path.write_text

    def tracking_write_text(self, content, encoding="utf-8"):
        if self.name.startswith(".todo.json") and self.name.endswith(".tmp"):
            temp_files_created.append(self.name)
        return original_write_text(self, content, encoding=encoding)

    with patch.object(Path, "write_text", tracking_write_text):
        storage.save(todos)

    # Temp filename should include PID
    assert len(temp_files_created) == 1
    temp_filename = temp_files_created[0]
    expected_pid = str(os.getpid())
    assert expected_pid in temp_filename, (
        f"Temp filename '{temp_filename}' should include PID '{expected_pid}' "
        f"to avoid cross-process collisions"
    )


def test_save_cleans_up_stale_temp_files(tmp_path) -> None:
    """Test that save() removes existing stale temp files from dead processes."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos1 = [Todo(id=1, text="original")]
    storage.save(todos1)

    # Simulate stale temp files from crashed processes
    # These should be cleaned up before writing new data
    stale_temp_1 = db.parent / f".{db.name}.12345.tmp"
    stale_temp_2 = db.parent / f".{db.name}.67890.tmp"

    stale_temp_1.write_text('{"stale": "data"}', encoding="utf-8")
    stale_temp_2.write_text('{"also": "stale"}', encoding="utf-8")

    assert stale_temp_1.exists()
    assert stale_temp_2.exists()

    # Save new data - should clean up stale temps
    todos2 = [Todo(id=1, text="new data")]
    storage.save(todos2)

    # Stale temps should be cleaned up
    assert not stale_temp_1.exists(), "Stale temp file should be cleaned up"
    assert not stale_temp_2.exists(), "Stale temp file should be cleaned up"

    # But the new data should be saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new data"


def test_temp_file_cleaned_on_replace_failure(tmp_path) -> None:
    """Test that temp file is cleaned up in finally block if os.replace fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    temp_files_created = []

    # Track temp file creation to get its path
    original_write_text = Path.write_text

    def tracking_write_text(self, content, encoding="utf-8"):
        if self.name.startswith(".todo.json") and self.name.endswith(".tmp"):
            temp_files_created.append(self)
        return original_write_text(self, content, encoding=encoding)

    # Mock os.replace to fail after temp file is written
    with (
        patch.object(Path, "write_text", tracking_write_text),
        patch("flywheel.storage.os.replace", side_effect=OSError("Simulated replace failure")),
        pytest.raises(OSError, match="Simulated replace failure"),
    ):
        storage.save(todos)

    # Temp file should be cleaned up despite the exception
    assert len(temp_files_created) == 1
    temp_path = temp_files_created[0]
    assert not temp_path.exists(), (
        f"Temp file '{temp_path}' should be cleaned up after os.replace failure"
    )


def _multiprocess_worker(
    db_path_str: str, pid: int, result_queue: multiprocessing.Queue
) -> None:
    """Worker function that writes to shared todo file.

    Defined at module level to be picklable for multiprocessing.
    """
    storage = TodoStorage(db_path_str)
    todos = [Todo(id=pid, text=f"Process {pid}")]
    try:
        storage.save(todos)
        result_queue.put(("success", pid))
    except Exception as e:
        result_queue.put(("error", pid, str(e)))


def test_concurrent_multiprocess_write_safety(tmp_path) -> None:
    """Test two separate TodoStorage objects writing to same file concurrently.

    This simulates multi-process scenario where each process has its own
    TodoStorage instance but writes to the same file.
    """
    import multiprocessing as mp

    db = tmp_path / "todo.json"

    # Use processes (not threads) to get different PIDs
    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue()

    # Create multiple workers that will try to write concurrently
    processes = []
    for i in range(1, 4):
        p = ctx.Process(target=_multiprocess_worker, args=(str(db), i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=5)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # At least one process should succeed
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(successes) > 0, f"At least one process should succeed, got: {results}"
    assert len(errors) == 0, f"No errors should occur, got: {errors}"

    # Final file should be valid JSON
    storage = TodoStorage(str(db))
    loaded = storage.load()
    assert isinstance(loaded, list)

    # File should contain at least one valid todo
    assert len(loaded) >= 1
