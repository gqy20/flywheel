"""Tests for Todo.__eq__ and __hash__ methods (Issue #4287).

These tests verify that:
1. Todo objects are compared by id only (same id = equal)
2. Todo objects can be used in sets for deduplication
3. Todo objects with different ids are not equal
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_equal() -> None:
    """Todos with same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_eq_different_id_not_equal() -> None:
    """Todos with different ids should not be equal even with same text."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_hash_same_id_same_hash() -> None:
    """Todos with same id should have same hash for set deduplication."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_set_deduplication() -> None:
    """Todo objects should be deduplicated in sets based on id."""
    todo1 = Todo(id=1, text="first", done=False)
    todo2 = Todo(id=2, text="second", done=True)
    todo3 = Todo(id=1, text="third", done=True)  # Same id as todo1

    unique_todos = {todo1, todo2, todo3}

    assert len(unique_todos) == 2, f"Expected 2 unique todos, got {len(unique_todos)}"


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != 1, "Todo should not equal an int with same id value"
    assert todo != "buy milk", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "buy milk"}, "Todo should not equal a dict"
    assert todo is not None, "Todo should not equal None"


def test_todo_hash_consistent_across_field_changes() -> None:
    """Todo hash should remain consistent if id doesn't change."""
    todo = Todo(id=1, text="original", done=False)
    original_hash = hash(todo)

    # Modify other fields (note: this may update timestamps)
    todo.done = True

    # Hash should still be based on id only
    assert hash(todo) == original_hash, "Hash should remain consistent based on id"
