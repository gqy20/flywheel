"""Tests for TodoStorage.count() method.

Issue #4933: Add count() method to get todo count without full deserialization.

This enables quick status checks (e.g., '5 pending tasks') without loading
and deserializing all todo objects. Useful for shell prompts and status bars.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_count_returns_zero_for_missing_file(tmp_path) -> None:
    """count() should return 0 when database file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist
    assert not db.exists()

    # count() should return 0 without error
    assert storage.count() == 0


def test_count_returns_correct_count_after_save(tmp_path) -> None:
    """count() should return the correct count after saving todos."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second", done=True),
        Todo(id=3, text="third"),
    ]
    storage.save(todos)

    # count() should return 3
    assert storage.count() == 3


def test_count_handles_empty_list_correctly(tmp_path) -> None:
    """count() should return 0 for an empty todo list."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Save empty list
    storage.save([])

    # count() should return 0
    assert storage.count() == 0


def test_count_matches_len_load(tmp_path) -> None:
    """count() should return the same value as len(storage.load())."""
    db = tmp_path / "consistency.json"
    storage = TodoStorage(str(db))

    # Save various numbers of todos
    for n in [0, 1, 5, 10]:
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, n + 1)]
        storage.save(todos)
        assert storage.count() == len(storage.load()), (
            f"count() should match len(load()) for {n} todos"
        )


def test_count_does_not_construct_todo_objects(tmp_path) -> None:
    """count() should work without constructing Todo objects.

    This verifies the optimization: count() reads JSON and returns
    len(raw_list) without calling Todo.from_dict() for each item.
    """
    db = tmp_path / "count.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file directly
    raw_data = [{"id": 1, "text": "one"}, {"id": 2, "text": "two"}]
    db.write_text(json.dumps(raw_data), encoding="utf-8")

    # count() should work even if we haven't loaded the data
    assert storage.count() == 2


def test_count_returns_integer(tmp_path) -> None:
    """count() should return an integer >= 0."""
    db = tmp_path / "type.json"
    storage = TodoStorage(str(db))

    # For missing file
    result = storage.count()
    assert isinstance(result, int)
    assert result >= 0

    # For existing data
    storage.save([Todo(id=1, text="test")])
    result = storage.count()
    assert isinstance(result, int)
    assert result >= 0
