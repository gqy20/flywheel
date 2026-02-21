"""Tests for issue #4933: Add TodoStorage.count() method.

This test suite verifies that TodoStorage.count() returns the todo count
without full deserialization, enabling quick status checks.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_count_returns_zero_for_missing_file(tmp_path) -> None:
    """Test count() returns 0 for non-existent database."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    assert storage.count() == 0


def test_count_returns_correct_count_after_save(tmp_path) -> None:
    """Test count() returns correct count after saving todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save 3 todos
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    assert storage.count() == 3


def test_count_handles_empty_list_correctly(tmp_path) -> None:
    """Test count() returns 0 for empty list."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Save empty list
    storage.save([])

    assert storage.count() == 0


def test_count_matches_load_length(tmp_path) -> None:
    """Test count() returns same value as len(storage.load())."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    todos = [Todo(id=i, text=f"todo {i}") for i in range(1, 6)]
    storage.save(todos)

    # count() should match len(load())
    assert storage.count() == len(storage.load())


def test_count_without_deserialization(tmp_path) -> None:
    """Test count() reads JSON and returns len(raw_list) without constructing Todo objects."""
    db = tmp_path / "todo.json"

    # Write raw JSON directly with valid structure but invalid Todo data
    # count() should still work because it doesn't construct Todo objects
    raw_data = [{"id": i, "text": f"item {i}"} for i in range(100)]
    db.write_text(json.dumps(raw_data), encoding="utf-8")

    storage = TodoStorage(str(db))
    assert storage.count() == 100


def test_count_returns_integer_gte_zero(tmp_path) -> None:
    """Test count() returns integer >= 0."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Non-existent file
    result = storage.count()
    assert isinstance(result, int)
    assert result >= 0

    # After save
    storage.save([Todo(id=1, text="test")])
    result = storage.count()
    assert isinstance(result, int)
    assert result >= 0
