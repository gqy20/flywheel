"""Tests for Todo.__eq__ and __hash__ methods (Issue #3030).

These tests verify that:
1. Todo objects are compared by id (not object identity)
2. Todo objects can be used in sets for deduplication
3. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_equal() -> None:
    """Two Todos with the same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_eq_different_id_not_equal() -> None:
    """Two Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=True)
    todo2 = Todo(id=2, text="same text", done=True)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_eq_same_object_equal() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="task")
    assert todo == todo, "Todo should be equal to itself"


def test_todo_eq_not_equal_to_other_types() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")
    assert todo != 1, "Todo should not equal an int"
    assert todo != "task", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "task"}, "Todo should not equal a dict"


def test_todo_hash_same_id_equal() -> None:
    """Two Todos with the same id should have the same hash."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_id_different() -> None:
    """Two Todos with different ids should (usually) have different hashes."""
    todo1 = Todo(id=1, text="text")
    todo2 = Todo(id=2, text="text")

    # Not a strict requirement, but expected behavior
    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_set_deduplication() -> None:
    """Todo objects should be deduplicated in a set based on id."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)
    todo3 = Todo(id=2, text="another task")

    unique_todos = {todo1, todo2, todo3}

    assert len(unique_todos) == 2, f"Expected 2 unique todos, got {len(unique_todos)}"
    # Both should be present in the set
    assert todo1 in unique_todos
    assert todo2 in unique_todos
    assert todo3 in unique_todos


def test_todo_set_membership() -> None:
    """Todo membership in set should work based on id equality."""
    todo = Todo(id=1, text="task")
    todo_set = {todo}

    # Different instance with same id should be found in set
    todo_same_id = Todo(id=1, text="different text")
    assert todo_same_id in todo_set, "Todo with same id should be found in set"


def test_todo_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="key1")
    todo2 = Todo(id=2, text="key2")

    mapping = {todo1: "value1", todo2: "value2"}

    assert mapping[todo1] == "value1"
    assert mapping[todo2] == "value2"

    # Different instance with same id should map to same value
    todo1_copy = Todo(id=1, text="different text")
    assert mapping[todo1_copy] == "value1", "Todo with same id should map to same dict value"
