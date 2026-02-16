"""Tests for Todo.__eq__ and __hash__ methods (Issue #3750).

These tests verify that:
1. Todo objects with the same id are equal regardless of other fields
2. Todo objects with different ids are not equal
3. Todo objects can be used in sets (hashable)
4. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_by_id() -> None:
    """Todo objects with the same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task b", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=False)
    todo2 = Todo(id=2, text="same text", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_hash_consistent_with_equality() -> None:
    """Todo objects with the same id should have the same hash."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task b", done=True)

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_set_deduplication() -> None:
    """Todo objects should be deduplicated in sets based on id."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task b", done=True)
    todo3 = Todo(id=2, text="task c", done=False)

    unique_todos = {todo1, todo2, todo3}

    assert len(unique_todos) == 2, f"Expected 2 unique todos, got {len(unique_todos)}"


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task b", done=True)

    # Using todos as keys should work
    todo_map = {todo1: "first value"}

    # todo2 should map to the same key since they have the same id
    todo_map[todo2] = "second value"

    # Should only have one entry since todo1 == todo2
    assert len(todo_map) == 1, f"Expected 1 entry, got {len(todo_map)}"
    assert todo_map[todo1] == "second value"


def test_todo_hash_different_ids() -> None:
    """Todo objects with different ids should (likely) have different hashes."""
    todo1 = Todo(id=1, text="same text", done=False)
    todo2 = Todo(id=2, text="same text", done=False)

    # While not strictly required, different ids should generally produce different hashes
    # This is a quality check, not a hard requirement
    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_equality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task", done=False)

    assert todo != 1, "Todo should not equal an int"
    assert todo != "task", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "task"}, "Todo should not equal a dict"
    assert todo is not None, "Todo should not be None"
