"""Regression test for issue #4131: TOCTOU race condition in load().

Tests that load() handles FileNotFoundError gracefully when a file
is deleted between the exists() check and the stat()/read_text() call.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage


def test_load_handles_stat_file_not_found(tmp_path) -> None:
    """Regression test for issue #4131: TOCTOU race condition.

    Verifies that load() returns [] instead of raising FileNotFoundError
    when stat() raises FileNotFoundError (file deleted after exists() returns True).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid file that exists
    db.write_text('[]', encoding="utf-8")

    # Simulate race condition: file exists during exists() check,
    # but stat() raises FileNotFoundError (file was deleted in between)
    call_count = [0]
    original_stat = Path.stat

    def mock_stat(self, **kwargs):
        """Simulate file being deleted between exists() check and stat() call."""
        call_count[0] += 1
        if self == db and call_count[0] >= 2:  # First call is from exists(), second from our code
            raise FileNotFoundError(f"[Errno 2] No such file or directory: '{self}'")
        return original_stat(self, **kwargs)

    with patch.object(Path, "stat", mock_stat):
        # load() should handle FileNotFoundError gracefully and return []
        result = storage.load()

    # The fix: load() should return empty list instead of raising FileNotFoundError
    assert result == [], "load() should return [] when file disappears between exists() and stat()"


def test_load_handles_read_text_file_not_found(tmp_path) -> None:
    """Test that load() handles file being deleted during the read operation.

    This tests the edge case where file exists and stat() succeeds,
    but then the file is deleted before read_text() is called.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    db.write_text('[]', encoding="utf-8")

    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        """Delete file during read_text to simulate race condition."""
        if self == db:
            raise FileNotFoundError(f"[Errno 2] No such file or directory: '{self}'")
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", mock_read_text):
        # load() should handle FileNotFoundError gracefully
        result = storage.load()

    assert result == [], "load() should return [] when file disappears during read"


def test_load_returns_empty_for_nonexistent_file(tmp_path) -> None:
    """Baseline test: load() returns [] for a file that doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist
    assert not db.exists()

    # load() should return empty list
    result = storage.load()
    assert result == []
