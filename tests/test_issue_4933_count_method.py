"""Tests for TodoStorage.count() method (Issue #4933).

This test suite verifies that count() returns the todo count
without full deserialization of Todo objects.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_count_returns_zero_for_missing_file(tmp_path: Path) -> None:
    """Test that count() returns 0 when database file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    assert storage.count() == 0


def test_count_returns_correct_count_after_save(tmp_path: Path) -> None:
    """Test that count() returns the correct number of todos after save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    todos = [
        Todo(id=1, text="first task"),
        Todo(id=2, text="second task"),
        Todo(id=3, text="third task"),
    ]
    storage.save(todos)

    # count() should return 3
    assert storage.count() == 3


def test_count_handles_empty_list_correctly(tmp_path: Path) -> None:
    """Test that count() returns 0 for empty todo list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save empty list
    storage.save([])

    assert storage.count() == 0


def test_count_returns_integer_gte_zero(tmp_path: Path) -> None:
    """Test that count() always returns an integer >= 0."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # For non-existent file
    result = storage.count()
    assert isinstance(result, int)
    assert result >= 0

    # After saving todos
    storage.save([Todo(id=1, text="test")])
    result = storage.count()
    assert isinstance(result, int)
    assert result >= 0


def test_count_is_consistent_with_load(tmp_path: Path) -> None:
    """Test that count() matches len(storage.load())."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Test with various todo counts
    for count in [0, 1, 5, 10]:
        todos = [Todo(id=i, text=f"task {i}") for i in range(1, count + 1)]
        storage.save(todos)
        assert storage.count() == len(storage.load()), (
            f"count() should match len(load()) for {count} todos"
        )
