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


def test_save_with_stale_temp_file_from_previous_crash(tmp_path) -> None:
    """Test that save() handles stale temp files from previous crashes.

    This is a security test: a stale temp file from a crashed process
    should be safely handled, not silently overwritten which could lose
    data from another concurrent process.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a stale temp file as if from a previous crashed process
    # Use a different PID to simulate another process
    fake_pid = 99999  # Unlikely to be current PID
    temp_path = db.with_name(f".{db.name}.{fake_pid}.tmp")
    stale_content = '{"stale": "data from crashed process"}'
    temp_path.write_text(stale_content, encoding="utf-8")

    # Save should handle the stale temp file safely
    todos = [Todo(id=1, text="new data")]
    storage.save(todos)

    # Verify the save succeeded and we have the correct data
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new data"

    # Verify the stale temp file was cleaned up
    assert not temp_path.exists(), "Stale temp file should be cleaned up after successful save"

    # Verify no other temp files are left behind
    import os as os_module
    current_pid = os_module.getpid()
    current_temp_path = db.with_name(f".{db.name}.{current_pid}.tmp")
    assert not current_temp_path.exists(), "Current temp file should also be cleaned up"


def test_temp_file_has_process_unique_name(tmp_path) -> None:
    """Test that temp filename includes process-unique component.

    Using deterministic temp names like '.todo.json.tmp' causes cross-process
    collisions. The temp name should include PID or UUID to be unique per process.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    temp_files_created = []
    original_write_text = Path.write_text

    def tracking_write_text(self, content, encoding="utf-8", **kwargs):
        if self.name.startswith(".todo.json") and self.name.endswith(".tmp"):
            temp_files_created.append(self)
        return original_write_text(self, content, encoding=encoding, **kwargs)

    with patch.object(Path, "write_text", tracking_write_text):
        storage.save([Todo(id=1, text="test")])

    # Verify temp filename contains process-unique component (PID)
    assert len(temp_files_created) == 1
    temp_name = temp_files_created[0].name
    import os as os_module
    pid = os_module.getpid()
    # Temp filename should include PID to avoid cross-process collision
    assert str(pid) in temp_name, f"Temp filename {temp_name} should include PID {pid} for process isolation"


def test_temp_file_cleanup_on_replace_failure(tmp_path) -> None:
    """Test that temp file is cleaned up if os.replace fails.

    If the atomic rename fails, the temp file should be cleaned up
    to prevent accumulation of orphaned temp files.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="initial")])

    # Track temp file path
    temp_path = None

    def failing_replace(src, dst):
        nonlocal temp_path
        temp_path = Path(src)
        # Simulate os.replace failure
        raise OSError("Simulated os.replace failure")

    with (
        patch("flywheel.storage.os.replace", failing_replace),
        pytest.raises(OSError, match=r"Simulated os.replace failure"),
    ):
        storage.save([Todo(id=2, text="new")])

    # Verify temp file was cleaned up even though os.replace failed
    assert temp_path is not None, "Temp file should have been created"
    assert not temp_path.exists(), "Temp file should be cleaned up after os.replace failure"
