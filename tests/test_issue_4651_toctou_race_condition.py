"""Regression test for issue #4651: TOCTOU race condition in load().

This test verifies that load() uses a single stat() call wrapped in
try/except FileNotFoundError instead of separate exists() + stat() calls,
which creates a race window between the check and use.

The race condition occurs when:
1. exists() returns True
2. Another process deletes the file
3. stat() raises FileNotFoundError
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_uses_single_stat_call_not_exists_plus_stat(tmp_path) -> None:
    """Test that load() uses a single stat() call, not exists() + stat().

    This verifies the fix for issue #4651 where load() had a TOCTOU race
    condition between exists() and stat() calls.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track which methods are called during load()
    called_methods = []

    original_exists = Path.exists
    original_stat = Path.stat

    def tracking_exists(self):
        called_methods.append("exists")
        return original_exists(self)

    def tracking_stat(self, *args, **kwargs):
        called_methods.append("stat")
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "exists", tracking_exists), patch.object(Path, "stat", tracking_stat):
        loaded = storage.load()

    # After the fix, load() should NOT call exists() separately
    # It should only call stat() and handle FileNotFoundError
    assert "stat" in called_methods, "load() should call stat()"
    assert "exists" not in called_methods, (
        "load() should not call exists() separately - use single stat() with exception handling"
    )

    # Verify data is correct
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_load_handles_file_deleted_after_stat_gracefully(tmp_path) -> None:
    """Test that load() handles FileNotFoundError when file is deleted.

    This simulates the race condition: file exists during stat() but
    is deleted before read_text(). The fix should propagate the
    FileNotFoundError as specified in the acceptance criteria.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    def read_text_that_raises_filenotfound(self, *args, **kwargs):
        """Simulate file being deleted between stat() and read_text()."""
        raise FileNotFoundError("File deleted during race window")

    with (
        patch.object(Path, "read_text", read_text_that_raises_filenotfound),
        pytest.raises(FileNotFoundError, match="File deleted during race window"),
    ):
        storage.load()


def test_load_returns_empty_list_when_file_not_found(tmp_path) -> None:
    """Test that load() returns empty list when file doesn't exist.

    This is the expected behavior when using stat() with FileNotFoundError
    handling instead of exists() + stat().
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist - should return empty list without raising
    loaded = storage.load()
    assert loaded == []


def test_load_handles_stat_raises_filenotfound(tmp_path) -> None:
    """Test that load() handles FileNotFoundError from stat() gracefully.

    This simulates the race condition: file is deleted right before stat()
    is called. The fix should catch FileNotFoundError and return [].
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    def stat_that_raises_filenotfound(self, *args, **kwargs):
        """Simulate file being deleted right before stat()."""
        raise FileNotFoundError("File deleted right before stat()")

    with patch.object(Path, "stat", stat_that_raises_filenotfound):
        # After fix: should return [] instead of raising
        loaded = storage.load()
        assert loaded == []


def test_load_no_race_window_between_check_and_use(tmp_path) -> None:
    """Test that there is no race window between existence check and file access.

    This test verifies the atomic nature of the fix: load() should use
    a single operation to check file existence and get file info.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track call sequence to ensure atomicity
    call_sequence = []

    original_exists = Path.exists
    original_stat = Path.stat

    def tracking_exists(self):
        call_sequence.append("exists")
        return original_exists(self)

    def tracking_stat(self, *args, **kwargs):
        call_sequence.append("stat")
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "exists", tracking_exists), patch.object(Path, "stat", tracking_stat):
        storage.load()

    # The sequence should be: stat (possibly multiple times internally)
    # but NOT: exists followed by stat
    # If exists is called before stat, that's the race condition
    if "exists" in call_sequence:
        pytest.fail(
            f"Race condition detected: exists() called before stat(). "
            f"Call sequence: {call_sequence}"
        )
