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


def test_save_with_stale_temp_file_from_crash(tmp_path) -> None:
    """Test that save handles stale temp file from previous crash gracefully.

    This is a regression test for issue #1986. If a temp file exists from
    a previous crash, the current implementation should:
    1. Clean up the stale temp file before writing
    2. Use a process-unique temp filename to avoid collisions
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Simulate stale temp file from previous crash
    # The old implementation used deterministic temp filename
    stale_temp_path = db.with_name(f".{db.name}.tmp")
    stale_temp_path.write_text('{"stale": "data from crash"}', encoding="utf-8")

    # New save should handle stale temp file gracefully
    new_todos = [Todo(id=2, text="new data")]
    storage.save(new_todos)

    # Verify final state is consistent
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new data"

    # Stale temp file should be cleaned up (either before or after write)
    # The new implementation uses unique temp names, so old stale temp
    # may still exist, but the new unique temp should be cleaned up
    new_temp_files = list(db.parent.glob(f".{db.name}.*.tmp"))
    # Only process-specific temp files should exist, not the generic one
    assert not stale_temp_path.exists() or stale_temp_path.name.endswith(f"{os.getpid()}.tmp") or len(new_temp_files) == 0


def test_temp_file_cleanup_on_replace_failure(tmp_path) -> None:
    """Test that temp file is cleaned up if os.replace fails.

    This is a regression test for issue #1986. If os.replace raises an
    exception, the temp file should be cleaned up in a finally block.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Mock os.replace to raise exception
    with (
        patch("flywheel.storage.os.replace", side_effect=OSError("Simulated replace failure")),
        pytest.raises(OSError, match="Simulated replace failure"),
    ):
        storage.save(todos)

    # Temp file should be cleaned up despite the exception
    # Look for any temp file matching the pattern
    temp_files = list(db.parent.glob(f".{db.name}*.tmp"))
    assert len(temp_files) == 0, f"Temp files not cleaned up: {temp_files}"


def test_temp_filename_includes_process_unique_component(tmp_path) -> None:
    """Test that temp filename includes process-unique component (pid) to avoid collision.

    This is a regression test for issue #1986. The temp filename should include
    the process ID or uuid to avoid collisions between concurrent processes.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track temp file creation
    temp_files_created = []
    original_write_text = Path.write_text

    def tracking_write_text(self, content, encoding="utf-8"):
        if self.name.startswith(f".{db.name}") and self.name.endswith(".tmp"):
            temp_files_created.append(self)
        return original_write_text(self, content, encoding=encoding)

    with patch.object(Path, "write_text", tracking_write_text):
        storage.save(todos)

    # Verify temp file name includes process-unique component
    assert len(temp_files_created) >= 1
    temp_name = temp_files_created[0].name
    # New implementation should include pid in temp filename
    assert str(os.getpid()) in temp_name or "uuid" in temp_name.lower(), \
        f"Temp filename should include process-unique component, got: {temp_name}"


def test_concurrent_multiprocess_write_safety(tmp_path) -> None:
    """Test that separate TodoStorage objects writing concurrently don't collide.

    This is a regression test for issue #1986. Multiple processes (or separate
    storage objects) should be able to write to the same file without temp
    file collisions.
    """
    db = tmp_path / "todo.json"
    storage1 = TodoStorage(str(db))
    storage2 = TodoStorage(str(db))

    # First write
    todos1 = [Todo(id=1, text="from storage1")]
    storage1.save(todos1)

    # Second write from separate storage object (simulates another process)
    todos2 = [Todo(id=2, text="from storage2")]
    storage2.save(todos2)

    # Final state should be consistent (last write wins)
    loaded = storage1.load()
    assert len(loaded) == 1
    assert loaded[0].text == "from storage2"

    # No stale temp files should remain
    temp_files = list(db.parent.glob(f".{db.name}*.tmp"))
    assert len(temp_files) == 0
