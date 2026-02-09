"""Regression test for issue #2565: TOCTOU race condition in load().

This test verifies that TodoStorage.load() handles the case where a file
is deleted between the exists() check and stat() call gracefully.

The fix combines the exists() check and stat() call into a single try/except
block to eliminate the race condition window.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_missing_file_gracefully(tmp_path) -> None:
    """Test that load() returns [] when file doesn't exist (normal case)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_handles_file_deleted_between_exists_and_stat(tmp_path) -> None:
    """Regression test for issue #2565: TOCTOU race condition.

    Simulates the race condition where stat() raises FileNotFoundError
    (file deleted between operations). The fix should handle this gracefully
    by catching FileNotFoundError and returning [].
    """
    db = tmp_path / "race_condition.json"
    storage = TodoStorage(str(db))

    # Don't create the file - test the stat() FileNotFoundError path
    # Mock stat() to raise FileNotFoundError
    def failing_stat(self, *, follow_symlinks=True):
        raise FileNotFoundError("Simulated: file deleted")

    # Patch stat on the specific path instance
    with patch.object(type(db), "stat", failing_stat):
        # load() should handle FileNotFoundError gracefully and return []
        result = storage.load()
        assert result == []


def test_load_works_correctly_when_file_exists(tmp_path) -> None:
    """Test that load() works correctly when file exists (happy path)."""
    db = tmp_path / "existing.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].id == 1
    assert loaded[0].text == "first todo"
    assert loaded[0].done is False
    assert loaded[1].id == 2
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True


def test_load_with_read_text_race_condition(tmp_path) -> None:
    """Test that load() handles FileNotFoundError from read_text().

    This tests another possible race condition: file exists during stat()
    but is deleted before read_text() is called. The fix should handle this
    gracefully by returning [].
    """
    db = tmp_path / "race_read_text.json"
    storage = TodoStorage(str(db))

    # Create the file first
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    call_count = {"stat": 0, "read_text": 0}

    original_stat = Path.stat

    def tracking_stat(self, *, follow_symlinks=True):
        call_count["stat"] += 1
        return original_stat(self, follow_symlinks=follow_symlinks)

    def failing_read_text(self, *args, **kwargs):
        call_count["read_text"] += 1
        # Simulate file deleted after stat() but before read_text()
        raise FileNotFoundError("Simulated: file deleted before read_text()")

    with (
        patch.object(Path, "stat", tracking_stat),
        patch.object(Path, "read_text", failing_read_text),
    ):
        # load() should handle FileNotFoundError from read_text() gracefully
        result = storage.load()
        assert result == []

    # Verify stat was called (we got past the initial check)
    assert call_count["stat"] >= 1
