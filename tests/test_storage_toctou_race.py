"""Tests for TOCTOU race condition in TodoStorage.load().

This test suite verifies that load() handles race conditions where the file
is deleted between the existence check and the read operation.

Issue: #4734
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_between_exists_and_read(tmp_path) -> None:
    """Test that load() handles FileNotFoundError when file is deleted during load.

    This is a regression test for issue #4734: Race condition (TOCTOU) between
    file existence check and file read in load().

    The race condition occurs when:
    1. load() checks if file exists (it does)
    2. File is deleted by another process
    3. load() tries to read the file, causing FileNotFoundError

    The fix should handle FileNotFoundError gracefully by returning [].
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Simulate race condition: make read_text raise FileNotFoundError
    # after exists() returns True
    original_read_text = Path.read_text

    def race_condition_read_text(self, *args, **kwargs):
        if self == db:
            raise FileNotFoundError(f"File deleted during load: {self}")
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", race_condition_read_text):
        # Before fix: this would raise FileNotFoundError
        # After fix: this should return [] gracefully
        result = storage.load()

    # The load() should handle the FileNotFoundError and return []
    assert result == []


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Test that load() returns [] when file doesn't exist.

    This is expected behavior that should continue after the fix.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_handles_stat_race_condition(tmp_path) -> None:
    """Test that load() handles FileNotFoundError during stat() call.

    The stat() call for file size check could also fail if the file
    is deleted between exists() and stat().
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Simulate race condition: make stat raise FileNotFoundError
    original_stat = Path.stat

    def race_condition_stat(self, *args, **kwargs):
        if self == db:
            raise FileNotFoundError(f"File deleted during stat: {self}")
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", race_condition_stat):
        # Before fix: this would raise FileNotFoundError
        # After fix: this should return [] gracefully
        result = storage.load()

    # The load() should handle the FileNotFoundError and return []
    assert result == []
