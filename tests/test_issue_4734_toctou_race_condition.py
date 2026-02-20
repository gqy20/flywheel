"""Tests for issue #4734: TOCTOU race condition in TodoStorage.load().

This test suite verifies that TodoStorage.load() handles the race condition
where a file may be deleted between the existence check and the read operation.
The fix removes the exists() check and handles FileNotFoundError directly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_returns_empty_list_on_nonexistent_file(tmp_path: Path) -> None:
    """Test that load() returns [] when file doesn't exist.

    This is the expected behavior - no exists() check needed,
    just handle FileNotFoundError directly.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist - should return empty list, not raise
    result = storage.load()
    assert result == []


def test_load_handles_file_deleted_after_stat(tmp_path: Path) -> None:
    """Test that load() handles FileNotFoundError during read operation.

    This simulates the TOCTOU race condition: file exists at stat() time
    but is deleted before read_text() is called.
    """
    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Create a valid file first
    storage.save([Todo(id=1, text="test")])

    # Mock read_text to simulate file being deleted between stat and read
    original_read_text = Path.read_text

    def mock_read_text_that_fails(self, *args, **kwargs):
        # Only fail for our specific file
        if self == db:
            raise FileNotFoundError(f"File deleted: {self}")
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", mock_read_text_that_fails):
        # Should return [] instead of raising FileNotFoundError
        result = storage.load()
        assert result == []


def test_load_handles_file_deleted_between_exists_and_stat(tmp_path: Path) -> None:
    """Test that load() handles FileNotFoundError during stat() operation.

    This simulates the race condition where file exists but stat() fails
    because the file was deleted in between.
    """
    db = tmp_path / "race2.json"
    storage = TodoStorage(str(db))

    # Create a valid file first
    storage.save([Todo(id=1, text="test")])

    # Mock stat to simulate file being deleted
    original_stat = Path.stat

    def mock_stat_that_fails(self, *args, **kwargs):
        if self == db:
            raise FileNotFoundError(f"File deleted during stat: {self}")
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", mock_stat_that_fails):
        # Should return [] instead of raising FileNotFoundError
        result = storage.load()
        assert result == []


def test_load_still_validates_json_on_existing_file(tmp_path: Path) -> None:
    """Verify that JSON validation still works after fixing the race condition."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create an invalid JSON file
    db.write_text("not valid json {", encoding="utf-8")

    # Should raise ValueError for invalid JSON
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()


def test_load_still_validates_json_list_format(tmp_path: Path) -> None:
    """Verify that list validation still works after fixing the race condition."""
    db = tmp_path / "not_list.json"
    storage = TodoStorage(str(db))

    # Create valid JSON that's not a list
    db.write_text('{"id": 1, "text": "wrong format"}', encoding="utf-8")

    # Should raise ValueError for non-list JSON
    with pytest.raises(ValueError, match="must be a JSON list"):
        storage.load()


def test_load_preserves_normal_functionality(tmp_path: Path) -> None:
    """Verify normal load/save functionality still works after the fix."""
    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Save some todos
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second", done=True),
    ]
    storage.save(todos)

    # Load and verify
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first"
    assert loaded[1].text == "second"
    assert loaded[1].done is True
