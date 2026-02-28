"""Regression test for issue #6269: TOCTOU race in load().

Tests that load() handles FileNotFoundError gracefully if the file
is deleted between the exists() check and the stat() call.

The fix removes the redundant exists() check and relies on FileNotFoundError
from stat() to handle the race condition properly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_before_stat(tmp_path) -> None:
    """Test that load() handles FileNotFoundError from stat() gracefully.

    This is a regression test for issue #6269.
    The original code had:
        if not self.path.exists():
            return []
        file_size = self.path.stat().st_size  # Could raise FileNotFoundError

    The TOCTOU race occurred because between exists() returning True and stat()
    being called, the file could be deleted, causing an unhandled FileNotFoundError.

    The fix removes the redundant exists() check and relies on FileNotFoundError
    from stat() directly, handling it gracefully by returning an empty list.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with valid content
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Simulate TOCTOU race: stat() raises FileNotFoundError (file deleted)
    original_stat = Path.stat
    original_exists = Path.exists

    call_count = {"stat": 0, "exists": 0}

    def patched_stat(self):
        call_count["stat"] += 1
        if self == db:
            # Simulate file being deleted when stat() is called
            raise FileNotFoundError(f"Simulated TOCTOU race: {self}")
        return original_stat(self)

    def patched_exists(self):
        call_count["exists"] += 1
        return original_exists(self)

    with (
        patch.object(Path, "stat", patched_stat),
        patch.object(Path, "exists", patched_exists),
    ):
        # load() should handle FileNotFoundError gracefully, not propagate it
        result = storage.load()

    # The fix should return an empty list when FileNotFoundError occurs
    # (file was deleted, so there's nothing to load)
    assert result == []
    # Verify stat() was called (the fixed code uses stat() first, not exists())
    assert call_count["stat"] >= 1
    # Verify exists() was NOT called - the fix removes the redundant check
    assert call_count["exists"] == 0


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Test that load() returns empty list for a non-existent file.

    This is the expected behavior when the file doesn't exist.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()

    assert result == []


def test_load_handles_file_deleted_before_read(tmp_path) -> None:
    """Test that load() handles file being deleted before read_text() is called.

    Another TOCTOU scenario: file exists for stat() but gets deleted
    before read_text() is called.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with valid content
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    original_read_text = Path.read_text

    def patched_read_text(self, *args, **kwargs):
        if self == db:
            # Simulate file being deleted before read
            raise FileNotFoundError(f"Simulated: file deleted before read: {self}")
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", patched_read_text):
        # load() should handle FileNotFoundError gracefully
        result = storage.load()

    # Should return empty list when file is deleted
    assert result == []
