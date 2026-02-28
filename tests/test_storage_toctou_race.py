"""Tests for TOCTOU race condition in TodoStorage.load().

This test suite verifies that the load() method handles the race condition
where a file is deleted between the exists() check and the stat() call.

Issue #6269: load() uses Path.stat() before Path.exists() check - potential TOCTOU race
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_between_exists_and_stat(tmp_path) -> None:
    """Regression test for issue #6269: TOCTOU race in load().

    Tests that if a file is deleted between the exists() check and the stat()
    call, FileNotFoundError is handled gracefully and returns empty list.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Verify file exists
    assert db.exists()

    # Simulate race condition: file gets deleted after exists() returns True
    # but before stat() is called
    call_count = [0]  # Using list for mutable closure capture

    def mock_exists(self):
        """Return True to pass exists check."""
        return True

    def mock_stat_raises_file_not_found(self):
        """Raise FileNotFoundError to simulate file deleted after exists()."""
        call_count[0] += 1
        raise FileNotFoundError(f"No such file or directory: {self}")

    with (
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "stat", mock_stat_raises_file_not_found),
    ):
        # Before fix: This would raise FileNotFoundError
        # After fix: This should return [] gracefully
        result = storage.load()

    # Should return empty list instead of raising
    assert result == []


def test_load_handles_file_deleted_between_exists_and_read_text(tmp_path) -> None:
    """Test that FileNotFoundError from read_text is also handled gracefully."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Simulate race: file exists, stat works, but read_text fails
    def mock_read_text_raises_file_not_found(self, encoding=None):
        """Raise FileNotFoundError to simulate file deleted after stat()."""
        raise FileNotFoundError(f"No such file or directory: {self}")

    with patch.object(Path, "read_text", mock_read_text_raises_file_not_found):
        # Before fix: This would raise FileNotFoundError
        # After fix: This should handle gracefully
        result = storage.load()

    # Should return empty list instead of raising
    assert result == []


def test_load_returns_empty_for_nonexistent_file(tmp_path) -> None:
    """Baseline test: load() returns empty list for non-existent file."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_concurrent_deletion_race(tmp_path) -> None:
    """Test load() handles file deletion during operation.

    This simulates the real-world race where another process deletes
    the file while load() is running.
    """
    import threading
    import time

    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="data")])

    deletion_happened = threading.Event()
    errors = []

    def delete_file_during_load():
        """Try to delete the file at a random time."""
        time.sleep(0.001)  # Small delay to let load() start
        try:
            db.unlink()
            deletion_happened.set()
        except FileNotFoundError:
            pass  # Already deleted

    # Patch exists to trigger deletion after check
    original_exists = Path.exists

    def exists_with_deletion(self):
        result = original_exists(self)
        if result and str(self) == str(db):
            # Start deletion thread after exists returns True
            t = threading.Thread(target=delete_file_during_load)
            t.start()
            time.sleep(0.002)  # Give time for deletion
        return result

    with patch.object(Path, "exists", exists_with_deletion):
        try:
            result = storage.load()
            # Should either return data or empty list, but not raise
            assert isinstance(result, list)
        except FileNotFoundError:
            # This is the bug - should not happen after fix
            errors.append("FileNotFoundError raised during race")

    assert not errors, f"Errors during race test: {errors}"
