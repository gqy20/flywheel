"""Tests for TodoStorage.exists() method.

Issue #5505: Add exists() method to quickly check if database file exists.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_does_not_exist(tmp_path) -> None:
    """Test that exists() returns False when database file does not exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    assert storage.exists() is False


def test_exists_returns_true_when_file_exists(tmp_path) -> None:
    """Test that exists() returns True when database file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create the file by saving some data
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    assert storage.exists() is True


def test_exists_consistent_with_load_behavior(tmp_path) -> None:
    """Test that exists() is consistent with load() behavior."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # When file doesn't exist, exists() returns False and load() returns empty list
    assert storage.exists() is False
    assert storage.load() == []

    # After saving, exists() returns True and load() returns the data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert storage.exists() is True
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_exists_with_default_path() -> None:
    """Test that exists() works with the default path."""
    storage = TodoStorage()  # Uses default .todo.json

    # The path attribute should be set correctly
    assert storage.path == Path(".todo.json")

    # exists() should return a boolean (actual value depends on whether file exists)
    result = storage.exists()
    assert isinstance(result, bool)
