"""Regression test for issue #4903: TOCTOU race condition in load().

The load() method has a Time-of-Check to Time-of-Use (TOCTOU) race condition:
1. Line 60: if not self.path.exists(): return []
2. Line 64: file_size = self.path.stat().st_size  # Can raise FileNotFoundError
3. Line 74: self.path.read_text()  # Can also raise FileNotFoundError

If the file is deleted between the exists() check and the stat()/read_text() calls,
a FileNotFoundError will be raised and propagate to the caller.

This test verifies that FileNotFoundError is caught and handled gracefully
by returning an empty list (consistent with the initial existence check).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage


def test_load_handles_file_deleted_after_exists_check(tmp_path) -> None:
    """Test that load() handles FileNotFoundError from stat() gracefully.

    Regression test for issue #4903: If a file is deleted between the
    exists() check and the stat() call, FileNotFoundError should be
    caught and handled gracefully (return empty list).
    """
    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    db.write_text('[]', encoding="utf-8")

    # Simulate file being deleted after exists() check but before stat()
    # We need to mock in a way that:
    # 1. exists() returns True (or we can't get past line 60)
    # 2. stat() raises FileNotFoundError
    # We'll mock the path.stat method only on the storage instance's path
    stat_call_count = [0]

    def stat_that_raises_after_exists(self, *args, **kwargs):
        stat_call_count[0] += 1
        raise FileNotFoundError("Simulated race condition in stat()")

    # Mock exists to return True, and stat to raise
    with (
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "stat", stat_that_raises_after_exists),
    ):
        # This should NOT raise FileNotFoundError
        # It should handle it gracefully by returning empty list
        result = storage.load()

    # Should return empty list instead of raising
    assert result == []
    # Verify stat was actually called (the race condition was simulated)
    assert stat_call_count[0] > 0


def test_load_handles_file_deleted_after_stat_check(tmp_path) -> None:
    """Test that load() handles FileNotFoundError from read_text() gracefully.

    Regression test for issue #4903: If a file is deleted between the
    stat() check and the read_text() call, FileNotFoundError should be
    caught and handled gracefully.
    """
    db = tmp_path / "race2.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    db.write_text('[]', encoding="utf-8")

    # Mock read_text to raise FileNotFoundError
    def read_text_that_raises(self, *args, **kwargs):
        raise FileNotFoundError("Simulated race condition in read_text")

    with patch.object(Path, "read_text", read_text_that_raises):
        # This should NOT raise FileNotFoundError
        # It should handle it gracefully by returning empty list
        result = storage.load()

    # Should return empty list instead of raising
    assert result == []


def test_load_normal_operation_not_affected(tmp_path) -> None:
    """Verify normal load() operation is not affected by the fix."""
    from flywheel.todo import Todo

    db = tmp_path / "normal.json"
    storage = TodoStorage(str(db))

    # Create a valid file with todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Normal load should work fine
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"

    # Loading from non-existent file should return empty list
    db.unlink()
    result = storage.load()
    assert result == []
