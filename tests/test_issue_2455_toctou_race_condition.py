"""Regression test for issue #2455: TOCTOU race condition in TodoStorage.load().

This test verifies that TodoStorage.load() handles concurrent file deletion
gracefully, without crashing due to the time-of-check to time-of-use (TOCTOU)
vulnerability between the exists() check and subsequent stat()/read_text() calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_between_exists_and_stat(tmp_path) -> None:
    """Test that load handles file deleted between exists() check and stat() call.

    This simulates a race condition where:
    1. exists() returns True (file exists)
    2. File is deleted by another process
    3. stat() is called and gets FileNotFoundError

    Expected: load() should handle this gracefully, returning empty list.
    """
    db = tmp_path / "race1.json"
    storage = TodoStorage(str(db))

    # Create a valid file first
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Verify normal load works (for sanity)
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"

    # Now physically delete the file after exists() would check
    # We'll mock exists() to return True, but the file is actually gone
    def mock_exists_returns_true(self):
        return True  # Lie about file existing

    with patch.object(Path, "exists", mock_exists_returns_true):
        # Delete the actual file so stat() will fail
        db.unlink()

        # This should handle the FileNotFoundError gracefully
        # by returning empty list (not crashing) - GREEN after fix
        result = storage.load()
        assert result == []


def test_load_handles_file_deleted_between_stat_and_read_text(tmp_path) -> None:
    """Test that load handles file deleted between stat() call and read_text() call.

    This simulates a race condition where:
    1. exists() returns True (file exists)
    2. stat() succeeds and returns valid size
    3. File is deleted by another process
    4. read_text() is called and gets FileNotFoundError

    Expected: load() should handle this gracefully by returning empty list.
    """
    db = tmp_path / "race2.json"
    storage = TodoStorage(str(db))

    # Create a valid file first
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Mock read_text() to simulate file deletion after stat()
    def mock_read_text_with_deletion(self, *args, **kwargs):
        # Simulate file was deleted between stat() and read_text()
        raise FileNotFoundError(f"[Errno 2] No such file or directory: '{self}'")

    # Simulate the race condition
    with patch.object(Path, "read_text", mock_read_text_with_deletion):
        # This should handle the FileNotFoundError gracefully
        # by returning empty list (not crashing) - GREEN after fix
        result = storage.load()
        assert result == []


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Test that load returns empty list when file doesn't exist (baseline)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist, should return empty list
    loaded = storage.load()
    assert loaded == []


def test_load_with_concurrent_deletion_threading_scenario(tmp_path) -> None:
    """Test load behavior under simulated concurrent deletion.

    This test uses a more realistic scenario where we patch exists() to
    return True initially but then cause all subsequent operations to fail,
    simulating a file being deleted immediately after the exists() check.

    Expected: load() should handle this gracefully by returning empty list.
    """
    db = tmp_path / "race3.json"
    storage = TodoStorage(str(db))

    # Create initial file
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Delete the file and mock exists() to return True
    # This simulates the race condition perfectly
    db.unlink()

    def mock_exists_returns_true(self):
        return True  # File "exists" (but was actually deleted)

    with patch.object(Path, "exists", mock_exists_returns_true):
        # Should handle gracefully by returning empty list - GREEN after fix
        result = storage.load()
        assert result == []
