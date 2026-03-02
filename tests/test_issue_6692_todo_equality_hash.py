"""Tests for Todo __eq__ and __hash__ methods (Issue #6692).

These tests verify that:
1. Todo objects with same content are equal
2. Todo objects are hashable (can be used in sets/dicts)
3. Todo objects can be deduplicated in sets based on equality
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_content() -> None:
    """Two Todos with same id/text/done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2, "Todos with identical content should be equal"


def test_todo_equality_different_done() -> None:
    """Two Todos with same id/text but different done should NOT be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2, "Todos with different 'done' status should not be equal"


def test_todo_inequality_different_id() -> None:
    """Two Todos with different id should NOT be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_inequality_different_text() -> None:
    """Two Todos with different text should NOT be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2, "Todos with different text should not be equal"


def test_todo_is_hashable() -> None:
    """Todo objects should be hashable."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Should not raise TypeError
    hash_value = hash(todo)

    # Hash should be based on id
    assert hash_value == hash(todo.id), "Hash should be based on id"


def test_todo_hash_consistency() -> None:
    """Hash of same Todo should be consistent."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert hash(todo1) == hash(todo2), "Equal Todos should have same hash"


def test_todo_set_deduplication() -> None:
    """Todo objects can be put in set() with correct deduplication."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same content as todo1
    todo3 = Todo(id=2, text="buy bread", done=False)  # Different

    todo_set = {todo1, todo2, todo3}

    # Should have 2 elements: one for id=1, one for id=2
    assert len(todo_set) == 2, f"Set should deduplicate equal Todos, got {len(todo_set)}"


def test_todo_dict_key_usage() -> None:
    """Todo objects can be used as dict keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same content as todo1

    todo_dict = {todo1: "first"}

    # todo2 should map to same key as todo1
    assert todo_dict[todo2] == "first", "Equal Todos should map to same dict entry"
