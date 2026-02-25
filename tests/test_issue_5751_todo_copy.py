"""Tests for Todo.copy() method (Issue #5751).

These tests verify that:
1. todo.copy() returns new Todo with identical fields
2. todo.copy(text='new') returns Todo with updated text field
3. Original Todo is unchanged after copy operations
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_equal_but_distinct_object() -> None:
    """copy() should return a new Todo with identical fields."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Should be equal in value
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at

    # But should be distinct objects
    assert copied is not original


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should override text field."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread")

    assert copied.id == original.id
    assert copied.text == "buy bread"
    assert copied.done == original.done
    assert copied.id == 1


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should override done field."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(done=True)

    assert copied.done is True
    assert original.done is False


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should accept multiple field overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread", done=True)

    assert copied.text == "buy bread"
    assert copied.done is True
    assert copied.id == original.id


def test_todo_copy_original_unchanged() -> None:
    """Original Todo should be unchanged after copy with modifications."""
    original = Todo(id=1, text="buy milk", done=False)
    original_updated_at = original.updated_at

    _ = original.copy(text="buy bread", done=True)

    # Original should remain unchanged
    assert original.text == "buy milk"
    assert original.done is False
    assert original.updated_at == original_updated_at


def test_todo_copy_preserves_created_at() -> None:
    """copy() should preserve created_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="new text")

    # created_at should be preserved
    assert copied.created_at == original.created_at


def test_todo_copy_with_all_field_overrides() -> None:
    """copy() should allow overriding all fields."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(id=2, text="new task", done=True)

    assert copied.id == 2
    assert copied.text == "new task"
    assert copied.done is True
    assert copied is not original
