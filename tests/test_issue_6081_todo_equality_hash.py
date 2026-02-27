"""Tests for Todo equality and hashing (Issue #6081)."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id() -> None:
    """Two Todo objects with the same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="First task", done=False)
    todo2 = Todo(id=1, text="Different text", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_different_ids() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="Same text", done=True)
    todo2 = Todo(id=2, text="Same text", done=True)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_can_be_used_in_set() -> None:
    """Todo objects should be usable in a set without errors."""
    todo1 = Todo(id=1, text="First", done=False)
    todo2 = Todo(id=1, text="Second", done=True)  # Same id, different content
    todo3 = Todo(id=2, text="Third", done=False)

    todo_set = {todo1, todo2, todo3}

    # Should only have 2 unique todos based on id
    assert len(todo_set) == 2, "Set should deduplicate based on id"


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="First", done=False)
    todo2 = Todo(id=1, text="Second", done=True)  # Same id, different content

    todo_dict = {todo1: "value1"}

    # Same id should map to same key
    todo_dict[todo2] = "value2"

    assert len(todo_dict) == 1, "Dict should have only one key for same id"
    assert todo_dict[todo1] == "value2", "Value should be updated"


def test_todo_equality_after_state_change() -> None:
    """Todo equality should remain consistent after state changes."""
    todo1 = Todo(id=1, text="Task")
    todo2 = Todo(id=1, text="Task")

    assert todo1 == todo2

    todo1.mark_done()

    # Even after state change, should still be equal based on id
    assert todo1 == todo2, "Equality should be based on id, not state"
