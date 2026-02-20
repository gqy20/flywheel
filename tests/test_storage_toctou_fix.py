"""Tests for TOCTOU race condition fix in TodoStorage.load().

This test suite verifies that load() handles the race condition between
checking if a file exists and calling stat() on it.

Issue #4651: TOCTOU race condition in load(): file existence check and
stat() are not atomic.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_between_exists_and_stat(tmp_path) -> None:
    """Test that load() gracefully handles file deletion between exists() and stat().

    This is a regression test for issue #4651: TOCTOU race condition.

    The race condition occurs when:
    1. exists() returns True
    2. File is deleted by another process
    3. stat() raises FileNotFoundError

    The fix should catch FileNotFoundError and treat it as if the file
    doesn't exist (return empty list).
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Track whether exists() was called
    original_exists = Path.exists
    call_count = [0]

    def mock_exists_with_race(self):
        """Mock exists() to return True, but file will be deleted before stat()."""
        if str(self) == str(db) and call_count[0] == 0:
            # First call returns True (file exists)
            call_count[0] += 1
            return True
        return original_exists(self)

    # Simulate file deletion between exists() and stat()
    def mock_stat_with_file_deletion(self):
        """Simulate FileNotFoundError as if file was deleted after exists()."""
        if str(self) == str(db):
            # Simulate the race: file existed when exists() checked, but
            # was deleted before stat() could run
            raise FileNotFoundError(f"Simulated race: {self} was deleted")
        return original_stat(self)

    original_stat = Path.stat

    with (
        patch.object(Path, "exists", mock_exists_with_race),
        patch.object(Path, "stat", mock_stat_with_file_deletion),
    ):
        # With the fix, this should return [] instead of raising FileNotFoundError
        result = storage.load()

    # The fix should handle the FileNotFoundError gracefully
    assert result == [], (
        "load() should return empty list when file is deleted between "
        "exists() and stat() (TOCTOU race condition)"
    )


def test_load_uses_single_stat_call_not_separate_exists_check(tmp_path) -> None:
    """Test that load() uses a single stat() call instead of separate exists() + stat().

    This verifies the fix for issue #4651: the atomic stat() pattern.

    The fix should:
    1. Call stat() once (not exists() + stat())
    2. Catch FileNotFoundError and return []
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track which methods are called
    calls = {"exists": 0, "stat": 0}
    original_exists = Path.exists
    original_stat = Path.stat

    def tracking_exists(self, *args, **kwargs):
        if str(self) == str(db):
            calls["exists"] += 1
        return original_exists(self, *args, **kwargs)

    def tracking_stat(self, *args, **kwargs):
        if str(self) == str(db):
            calls["stat"] += 1
        return original_stat(self, *args, **kwargs)

    with (
        patch.object(Path, "exists", tracking_exists),
        patch.object(Path, "stat", tracking_stat),
    ):
        storage.load()

    # With the fix, exists() should NOT be called for the file check
    # (it should use try/except around stat() instead)
    assert calls["exists"] == 0, (
        f"load() should not call exists() separately (called {calls['exists']} times). "
        "Use single stat() with try/except FileNotFoundError instead."
    )


def test_load_returns_empty_list_for_missing_file(tmp_path) -> None:
    """Test that load() returns empty list for a file that doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_raises_file_not_found_on_deletion_after_stat(tmp_path) -> None:
    """Test that load() raises appropriate error if file is deleted after stat().

    This is a different race: file exists during stat() but is deleted
    before read_text(). In this case, FileNotFoundError should be raised
    (not silently return []).

    This tests that the fix only handles the exists()-stat() race, not
    all file races.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    original_read_text = Path.read_text

    def mock_read_text_with_deletion(self, *args, **kwargs):
        """Simulate file deletion between stat() and read_text()."""
        if str(self) == str(db):
            raise FileNotFoundError(f"File deleted after stat: {self}")
        return original_read_text(self, *args, **kwargs)

    with (
        patch.object(Path, "read_text", mock_read_text_with_deletion),
        pytest.raises(FileNotFoundError),
    ):
        storage.load()


def test_load_handles_large_file_check_toctou_safe(tmp_path) -> None:
    """Test that the file size check in load() is TOCTOU-safe.

    Verifies that the file size check (to prevent DoS) doesn't have a
    race condition with file deletion.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create data
    todos = [Todo(id=1, text="test data")]
    storage.save(todos)

    original_stat = Path.stat
    stat_call_count = [0]

    def tracking_stat(self, *args, **kwargs):
        result = original_stat(self, *args, **kwargs)
        if str(self) == str(db):
            stat_call_count[0] += 1
        return result

    with patch.object(Path, "stat", tracking_stat):
        result = storage.load()

    # Should have successful load with size check from single stat
    assert len(result) == 1
    assert result[0].text == "test data"
    # Verify stat was called (for size check and file existence)
    assert stat_call_count[0] >= 1
