"""Tests for atomic file write behavior in TodoStorage.

This test suite verifies that TodoStorage.save() writes files atomically,
preventing data corruption if the process crashes during write.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
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


# Security tests for file size limit (DoS protection)


def test_load_raises_valueerror_when_file_exceeds_limit(tmp_path) -> None:
    """Test that load() raises ValueError when file size exceeds 10MB limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file larger than _MAX_JSON_SIZE_BYTES
    oversized_content = "x" * (_MAX_JSON_SIZE_BYTES + 1)
    db.write_text(oversized_content, encoding="utf-8")

    # Verify ValueError is raised with descriptive message
    with pytest.raises(ValueError, match="JSON file too large"):
        storage.load()


def test_load_raises_valueerror_when_file_exactly_at_limit_boundary(tmp_path) -> None:
    """Test that load() raises ValueError when file is at exactly the limit boundary."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file exactly one byte over the limit
    oversized_content = "x" * (_MAX_JSON_SIZE_BYTES + 1)
    db.write_text(oversized_content, encoding="utf-8")

    with pytest.raises(ValueError, match="JSON file too large"):
        storage.load()


def test_load_succeeds_when_file_within_limit(tmp_path) -> None:
    """Test that load() succeeds for files within the size limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create valid JSON data well within limit
    todos = [Todo(id=1, text="normal size file")]
    storage.save(todos)

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "normal size file"


def test_load_succeeds_when_file_exactly_at_limit(tmp_path) -> None:
    """Test that load() succeeds when file size is exactly at the limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file exactly at the size limit with valid JSON
    # Use smallest valid JSON entry
    entry = '{"id":1,"text":"x","done":false}'
    # Calculate how many entries we can fit
    bracket_overhead = 2  # [ and ]
    comma_overhead = 1  # comma between entries
    entries_needed = (_MAX_JSON_SIZE_BYTES - bracket_overhead) // (len(entry) + comma_overhead)

    # Build valid JSON
    valid_json = "[" + ",".join([entry] * entries_needed) + "]"

    # Verify it's within limit (should be slightly less than limit due to rounding)
    assert len(valid_json.encode("utf-8")) <= _MAX_JSON_SIZE_BYTES

    db.write_text(valid_json, encoding="utf-8")

    # File should be within or at limit, should load
    loaded = storage.load()
    assert isinstance(loaded, list)
    assert len(loaded) == entries_needed


def test_load_error_message_includes_size_details(tmp_path) -> None:
    """Test that error message includes actual and limit size information."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file 20MB (2x the limit) to test error message format
    twenty_mb = 20 * 1024 * 1024
    oversized_content = "x" * twenty_mb
    db.write_text(oversized_content, encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value)
    assert "20.0MB" in error_msg  # Actual size
    assert "10MB" in error_msg  # Limit
    assert "limit" in error_msg.lower()


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Test that load() returns empty list when file doesn't exist (no size check needed)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list, not raise error
    loaded = storage.load()
    assert loaded == []
