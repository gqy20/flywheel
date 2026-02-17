"""Tests for __hash__ support in Todo class (Issue #4064)."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_is_hashable() -> None:
    """Todo objects should be hashable."""
    todo = Todo(id=1, text="test task")
    # Should not raise TypeError
    hash_value = hash(todo)
    assert isinstance(hash_value, int)


def test_todo_can_be_used_in_set() -> None:
    """Todo objects should be usable as set elements."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todo3 = Todo(id=1, text="duplicate id")

    todo_set = {todo1, todo2, todo3}
    # Two todos with same id should be considered equal in set
    assert len(todo_set) == 2


def test_todo_can_be_used_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    todo_dict = {todo1: "value1", todo2: "value2"}
    assert todo_dict[todo1] == "value1"
    assert todo_dict[todo2] == "value2"


def test_todo_hash_is_based_on_id() -> None:
    """Todo hash should be based on the id field."""
    todo1 = Todo(id=42, text="task a")
    todo2 = Todo(id=42, text="task b")

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_consistency() -> None:
    """Todo hash should remain consistent across object lifetime."""
    todo = Todo(id=1, text="original")
    original_hash = hash(todo)

    # Modify mutable attributes
    todo.mark_done()
    todo.rename("renamed")

    # Hash should remain the same (based on id)
    assert hash(todo) == original_hash


def test_todo_dict_key_deduplication() -> None:
    """Dict with Todo keys should deduplicate by id."""
    todo1 = Todo(id=1, text="first")
    todo3 = Todo(id=1, text="same id as first")

    todo_dict = {todo1: "original", todo3: "overwritten"}
    # Both use same id, so second overwrites first
    assert len(todo_dict) == 1
    assert todo_dict[todo1] == "overwritten"
