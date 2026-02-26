"""Tests for Todo.copy method (Issue #5889).

These tests verify that:
1. todo.copy() returns a new Todo with identical fields
2. todo.copy({'done': True}) returns new Todo with done=True
3. Original Todo is unchanged after copy operation
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_new_instance() -> None:
    """copy() should return a new Todo instance, not the same object."""
    original = Todo(id=1, text="a")
    copy = original.copy()

    assert copy is not original
    assert isinstance(copy, Todo)


def test_todo_copy_preserves_all_fields() -> None:
    """copy() should return a Todo with identical fields."""
    original = Todo(id=1, text="original task", done=True)
    copy = original.copy()

    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_todo_copy_with_updates() -> None:
    """copy({'done': True}) should return new Todo with overridden field."""
    original = Todo(id=1, text="task", done=False)
    copy = original.copy({"done": True})

    assert copy.done is True
    assert original.done is False  # Original unchanged


def test_todo_copy_with_multiple_updates() -> None:
    """copy() should support overriding multiple fields."""
    original = Todo(id=1, text="old text", done=False)
    copy = original.copy({"text": "new text", "done": True})

    assert copy.text == "new text"
    assert copy.done is True
    assert original.text == "old text"
    assert original.done is False


def test_todo_copy_original_unchanged() -> None:
    """Original Todo should be unchanged after copy operation."""
    original = Todo(id=1, text="original", done=False)
    original_created_at = original.created_at
    original_updated_at = original.updated_at

    # Perform copy with updates
    _ = original.copy({"done": True, "text": "changed"})

    # Verify original is unchanged
    assert original.done is False
    assert original.text == "original"
    assert original.created_at == original_created_at
    assert original.updated_at == original_updated_at


def test_todo_copy_with_id_update() -> None:
    """copy() should support updating id field."""
    original = Todo(id=1, text="task")
    copy = original.copy({"id": 2})

    assert copy.id == 2
    assert original.id == 1


def test_todo_copy_with_empty_dict() -> None:
    """copy({}) should be equivalent to copy() with no arguments."""
    original = Todo(id=1, text="task", done=True)
    copy = original.copy({})

    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy is not original
