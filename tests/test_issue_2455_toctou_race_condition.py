"""Regression tests for issue #2455: TOCTOU race condition in TodoStorage.load().

This test suite verifies that the load() method handles race conditions where
the file is deleted between the existence check and the file operations.

Time-of-Check to Time-of-Use (TOCTOU) vulnerability occurs when:
1. File exists() check returns True
2. File is deleted by another process
3. stat() or read_text() fails with FileNotFoundError
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_after_exists_check(tmp_path) -> None:
    """Test that load() handles file deleted between exists() and stat().

    This tests the TOCTOU race condition where:
    1. exists() returns True
    2. File gets deleted
    3. stat() raises FileNotFoundError
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Mock exists() to return True (file was there)
    # But then stat() raises FileNotFoundError (file got deleted)
    with (
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "stat", side_effect=FileNotFoundError("Race condition")),
    ):
        # Should handle gracefully and return empty list
        result = storage.load()
        assert result == []


def test_load_handles_file_deleted_after_stat_check(tmp_path) -> None:
    """Test that load() handles file deleted between stat() and read_text().

    This tests the TOCTOU race condition where:
    1. exists() returns True
    2. stat() succeeds
    3. File gets deleted
    4. read_text() raises FileNotFoundError
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Create a mock stat result with valid size
    mock_stat_result = MagicMock()
    mock_stat_result.st_size = 100  # Small file

    with (
        patch.object(Path, "stat", return_value=mock_stat_result),
        patch.object(Path, "read_text", side_effect=FileNotFoundError("Race condition")),
    ):
        # Should handle gracefully and return empty list
        result = storage.load()
        assert result == []


def test_load_handles_file_deleted_during_both_operations(tmp_path) -> None:
    """Test load() when file is deleted during both stat() and read_text()."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    with (
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "stat", side_effect=FileNotFoundError("Deleted")),
    ):
        result = storage.load()
        assert result == []


def test_load_returns_empty_list_when_nonexistent_file(tmp_path) -> None:
    """Test that load() returns empty list for non-existent file (normal case)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_normal_operation_still_works(tmp_path) -> None:
    """Test that normal load operation still works after TOCTOU fix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first task"),
        Todo(id=2, text="second task", done=True),
    ]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first task"
    assert loaded[1].text == "second task"
    assert loaded[1].done is True


def test_load_still_raises_on_actual_errors(tmp_path) -> None:
    """Test that load() still raises appropriate exceptions for actual errors."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write invalid JSON
    db.write_text("{invalid json}", encoding="utf-8")

    # Should still raise ValueError for invalid JSON
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()


def test_load_concurrent_file_deletion_simulation(tmp_path) -> None:
    """Simulate a realistic concurrent deletion scenario.

    This test simulates file being deleted immediately after exists() check.
    We mock exists() to return True, but then stat() fails with FileNotFoundError.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create the file first
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Mock exists() to return True (file was there)
    # Then make stat() raise FileNotFoundError (file got deleted between check and use)
    def mock_exists(self):
        # exists() check in load() should succeed
        return True

    def mock_stat(self, follow_symlinks=True):
        # stat() call should fail (file was deleted)
        raise FileNotFoundError("Simulated race condition")

    with (
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "stat", mock_stat),
    ):
        result = storage.load()
        # Should return empty list, not crash
        assert result == []
