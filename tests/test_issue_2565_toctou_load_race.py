"""Regression tests for issue #2565: TOCTOU race condition in load().

Issue: exists() check followed by stat() call creates a race condition window
where the file could be deleted between the two operations.

These tests verify that load() handles FileNotFoundError gracefully from stat() call
and eliminates the race condition by combining operations.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage


def test_load_returns_empty_list_when_file_does_not_exist(tmp_path) -> None:
    """Issue #2565: load() should return [] when file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_returns_empty_list_when_file_deleted_between_exists_and_stat(tmp_path) -> None:
    """Issue #2565: load() should handle race where file is deleted after exists() check.

    This simulates the TOCTOU race condition by mocking stat() to raise FileNotFoundError
    even though exists() would return True.
    """
    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Create the file initially
    db.write_text("[]", encoding="utf-8")

    # Mock stat to simulate file being deleted between exists() and stat()
    original_stat = Path.stat

    def racing_stat(self):
        # First call (from exists()) succeeds, subsequent call fails
        # This simulates the race condition window
        if hasattr(racing_stat, "called"):
            raise FileNotFoundError(f"[Errno 2] No such file or directory: '{self}'")
        racing_stat.called = True
        return original_stat(self)

    with patch.object(Path, "stat", racing_stat):
        result = storage.load()

    # Should return [] instead of crashing
    assert result == []


def test_load_works_correctly_when_file_exists(tmp_path) -> None:
    """Issue #2565: load() should work correctly when file exists."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create valid JSON file
    db.write_text('[{"id": 1, "text": "test todo", "done": false}]', encoding="utf-8")

    result = storage.load()
    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].text == "test todo"


def test_load_with_concurrent_file_deletion(tmp_path) -> None:
    """Issue #2565: load() should handle concurrent file deletion gracefully.

    This test verifies that load() doesn't crash if the file is deleted.
    The exact timing is unpredictable, so we verify no exception is raised.
    """
    import threading
    import time

    db = tmp_path / "concurrent.json"
    storage = TodoStorage(str(db))

    # Create valid JSON file
    db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")

    def delete_file_repeatedly():
        """Repeatedly try to delete the file to maximize race chance."""
        for _ in range(100):
            time.sleep(0.0001)
            try:
                if db.exists():
                    db.unlink()
            except FileNotFoundError:
                pass

    # Start thread that will delete the file
    deleter = threading.Thread(target=delete_file_repeatedly, daemon=True)
    deleter.start()

    # Try to load - should not raise FileNotFoundError
    # After fix: should return [] or valid data, never crash
    result = storage.load()

    # Result should be either the loaded data or empty list
    # Never should have crashed with FileNotFoundError
    assert isinstance(result, list)

    deleter.join(timeout=2)


def test_load_respects_max_file_size_limit(tmp_path) -> None:
    """Issue #2565: load() should still enforce file size limit after fix."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the limit (10MB)
    large_content = "[]" + " " * (11 * 1024 * 1024)
    db.write_text(large_content, encoding="utf-8")

    with pytest.raises(ValueError, match="JSON file too large"):
        storage.load()
