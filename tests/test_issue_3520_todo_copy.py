"""Tests for Todo.copy() method (Issue #3520).

These tests verify that:
1. todo.copy() returns a new independent Todo object
2. todo.copy(**kwargs) can override fields
3. Original object is not affected by copy operations
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_independent_object() -> None:
    """copy() should return a new Todo object with same field values."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    # Copy should be a different object
    assert copy is not original
    # But have same field values
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at


def test_todo_copy_with_field_override() -> None:
    """copy(**kwargs) should return a copy with overridden fields."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(text="buy bread", done=True)

    # Copy should have overridden values
    assert copy.text == "buy bread"
    assert copy.done is True
    # Other fields should remain the same
    assert copy.id == original.id
    assert copy.created_at == original.created_at


def test_todo_copy_original_unchanged() -> None:
    """Modifying copy should not affect original object."""
    original = Todo(id=1, text="original text", done=False)
    original_created = original.created_at

    copy = original.copy(text="modified text", done=True)

    # Original should remain unchanged
    assert original.text == "original text"
    assert original.done is False
    assert original.created_at == original_created

    # Copy should have new values
    assert copy.text == "modified text"
    assert copy.done is True


def test_todo_copy_preserves_created_at() -> None:
    """copy() should preserve the original created_at timestamp."""
    original = Todo(id=1, text="task")
    copy = original.copy(text="new task")

    # created_at should be preserved
    assert copy.created_at == original.created_at


def test_todo_copy_multiple_times() -> None:
    """Should be able to create multiple independent copies."""
    original = Todo(id=1, text="original")

    copy1 = original.copy(text="copy1")
    copy2 = original.copy(text="copy2")

    # All should be different objects
    assert original is not copy1
    assert original is not copy2
    assert copy1 is not copy2

    # Each should have their own text
    assert original.text == "original"
    assert copy1.text == "copy1"
    assert copy2.text == "copy2"


def test_todo_copy_with_id_override() -> None:
    """copy() should allow overriding id field."""
    original = Todo(id=1, text="task")
    copy = original.copy(id=99)

    assert copy.id == 99
    assert original.id == 1
