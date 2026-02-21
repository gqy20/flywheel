"""Tests for issue #4822: Add count() method to return todo count without full load."""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_count_returns_zero_when_storage_file_does_not_exist(tmp_path) -> None:
    """count() returns 0 when storage file does not exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist yet
    assert not db.exists()

    # count() should return 0
    assert storage.count() == 0


def test_count_returns_correct_count_with_todos(tmp_path) -> None:
    """count() returns correct integer count of stored todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save 3 todos
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    # count() should return 3
    assert storage.count() == 3


def test_count_returns_zero_for_empty_storage(tmp_path) -> None:
    """count() returns 0 for empty storage file."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Save empty list
    storage.save([])

    # count() should return 0
    assert storage.count() == 0


def test_count_raises_value_error_for_corrupted_json(tmp_path) -> None:
    """count() raises ValueError for corrupted JSON (consistent with load())."""
    db = tmp_path / "corrupted.json"
    storage = TodoStorage(str(db))

    # Write invalid JSON
    db.write_text("not valid json {", encoding="utf-8")

    # count() should raise ValueError (consistent with load())
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.count()


def test_count_matches_load_length(tmp_path) -> None:
    """count() should return same value as len(load())."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    todos = [
        Todo(id=1, text="one"),
        Todo(id=2, text="two", done=True),
        Todo(id=3, text="three"),
        Todo(id=4, text="four", done=True),
        Todo(id=5, text="five"),
    ]
    storage.save(todos)

    # count() should match len(load())
    assert storage.count() == len(storage.load())
    assert storage.count() == 5
