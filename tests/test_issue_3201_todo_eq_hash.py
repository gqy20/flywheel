"""Tests for Todo.__eq__ and __hash__ methods (Issue #3201).

These tests verify that:
1. Todo objects with same fields compare as equal
2. Todo objects with different fields compare as not equal
3. Todo objects can be used in sets for deduplication
4. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_with_same_fields() -> None:
    """Two Todo objects with same fields should compare as equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 == todo2


def test_todo_eq_with_different_id() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_eq_with_different_text() -> None:
    """Two Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_eq_with_different_done() -> None:
    """Two Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_eq_with_different_timestamps() -> None:
    """Two Todo objects with different timestamps should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-02T00:00:00+00:00", updated_at="2024-01-02T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo is not None


def test_todo_hash_with_same_id() -> None:
    """Two Todo objects with same id should have same hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert hash(todo1) == hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todo objects with same fields should be deduplicated in a set."""
    timestamp = "2024-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="buy milk", done=False, created_at=timestamp, updated_at=timestamp)
    todo2 = Todo(id=1, text="buy milk", done=False, created_at=timestamp, updated_at=timestamp)
    todo3 = Todo(id=2, text="buy bread", done=False, created_at=timestamp, updated_at=timestamp)

    todo_set = {todo1, todo2, todo3}

    # Should have only 2 unique todos (todo1 and todo2 are equal)
    assert len(todo_set) == 2


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    timestamp = "2024-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="buy milk", done=False, created_at=timestamp, updated_at=timestamp)
    todo2 = Todo(id=1, text="buy milk", done=False, created_at=timestamp, updated_at=timestamp)
    todo3 = Todo(id=2, text="buy bread", done=False, created_at=timestamp, updated_at=timestamp)

    todo_dict = {todo1: "first", todo3: "second"}

    # todo2 should map to same key as todo1 since they are equal
    assert todo_dict[todo2] == "first"
    assert todo_dict[todo3] == "second"


def test_todo_hash_consistency() -> None:
    """Hash should be consistent across multiple calls."""
    todo = Todo(id=1, text="buy milk", done=False)

    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)

    assert hash1 == hash2 == hash3
