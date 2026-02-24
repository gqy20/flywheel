"""Tests for issue #5505: Add exists() method to TodoStorage.

This test suite verifies that TodoStorage.exists() provides a quick way to
check if the database file exists, without needing to call load() which
may have side effects.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_does_not_exist(tmp_path: Path) -> None:
    """Test that exists() returns False when database file does not exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File does not exist yet
    assert not db.exists()
    assert storage.exists() is False


def test_exists_returns_true_when_file_exists(tmp_path: Path) -> None:
    """Test that exists() returns True when database file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create the file by saving some todos
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Now file should exist
    assert db.exists()
    assert storage.exists() is True


def test_exists_consistent_with_load_behavior(tmp_path: Path) -> None:
    """Test that exists() behavior is consistent with load().

    When load() would return empty list (file doesn't exist), exists()
    should return False.
    When load() would return data, exists() should return True.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially, file doesn't exist
    assert storage.exists() is False
    assert storage.load() == []  # load returns empty list

    # After saving, file exists
    storage.save([Todo(id=1, text="saved")])
    assert storage.exists() is True
    assert len(storage.load()) == 1  # load returns data


def test_exists_with_custom_path(tmp_path: Path) -> None:
    """Test that exists() works correctly with custom database paths."""
    custom_db = tmp_path / "subdir" / "custom.json"
    storage = TodoStorage(str(custom_db))

    # File doesn't exist initially
    assert storage.exists() is False

    # Save creates the file (including parent directory)
    storage.save([Todo(id=1, text="custom path test")])

    # Now exists should return True
    assert storage.exists() is True


def test_exists_returns_bool_type(tmp_path: Path) -> None:
    """Test that exists() returns a proper bool type, not truthy value."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Should return actual bool False
    result_false = storage.exists()
    assert result_false is False
    assert isinstance(result_false, bool)

    # Create file and check True
    storage.save([Todo(id=1, text="test")])
    result_true = storage.exists()
    assert result_true is True
    assert isinstance(result_true, bool)
