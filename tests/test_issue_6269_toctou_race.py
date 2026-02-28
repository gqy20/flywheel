"""Tests for TOCTOU race condition fix in TodoStorage.load().

Issue #6269: load() uses Path.stat() before Path.exists() check - potential TOCTOU race.

The fix should handle the case where a file is deleted between the exists() check
and the stat() call, gracefully returning an empty list instead of raising
FileNotFoundError.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_after_exists_check(tmp_path) -> None:
    """Test that load() handles file deletion after the exists() check.

    This tests the TOCTOU (Time-Of-Check-Time-Of-Use) race condition where:
    1. exists() returns True (file exists at check time)
    2. File is deleted by another process
    3. stat() or read_text() raises FileNotFoundError

    The fix should catch FileNotFoundError and return an empty list,
    consistent with the behavior when the file doesn't exist initially.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Simulate TOCTOU race: file exists, then gets deleted during load
    # by mocking read_text to raise FileNotFoundError (file deleted after stat)
    def read_text_raises_not_found(self, *args, **kwargs):
        raise FileNotFoundError(f"Simulated deletion: {self}")

    with patch.object(Path, "read_text", read_text_raises_not_found):
        result = storage.load()

    # Should return empty list, not raise FileNotFoundError
    assert result == []


def test_load_raises_file_not_found_if_never_existed(tmp_path) -> None:
    """Test that load() correctly returns empty list when file never existed."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_raises_other_os_errors_normally(tmp_path) -> None:
    """Test that load() still raises other OS errors (not FileNotFoundError)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Simulate PermissionError during read_text()
    def read_text_permission_denied(self, *args, **kwargs):
        raise PermissionError(f"Permission denied: {self}")

    with (
        patch.object(Path, "read_text", read_text_permission_denied),
        pytest.raises(PermissionError),
    ):
        storage.load()


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Regression test: load() should return [] for non-existent file.

    This is the expected behavior after fixing the TOCTOU race by
    removing the redundant exists() check and relying on FileNotFoundError.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist - should return empty list
    result = storage.load()
    assert result == []
    assert not db.exists()
