"""Tests for Todo.copy() method (Issue #5751).

These tests verify that:
1. copy() returns a new Todo with identical fields
2. copy(text='new') returns a Todo with the updated text field
3. The original Todo is unchanged after copy operations
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_equal_but_distinct_object() -> None:
    """copy() should return a new Todo with identical fields but different object."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Should be equal in content
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at

    # But should be a different object
    assert copied is not original


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should return a Todo with updated text field."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread")

    # Text should be updated
    assert copied.text == "buy bread"

    # Other fields should remain the same
    assert copied.id == original.id
    assert copied.done == original.done
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should return a Todo with updated done field."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(done=True)

    # Done should be updated
    assert copied.done is True

    # Other fields should remain the same
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should accept multiple field overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread", done=True)

    # Both fields should be updated
    assert copied.text == "buy bread"
    assert copied.done is True

    # Other fields should remain the same
    assert copied.id == original.id
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at


def test_todo_copy_original_unchanged() -> None:
    """Original Todo should be unchanged after copy operations."""
    original = Todo(id=1, text="buy milk", done=False)
    original_text = original.text
    original_done = original.done

    # Perform copy with overrides
    original.copy(text="buy bread", done=True)

    # Original should be unchanged
    assert original.text == original_text
    assert original.done == original_done


def test_todo_copy_with_id_override() -> None:
    """copy() should allow overriding the id field."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(id=2)

    # ID should be updated
    assert copied.id == 2

    # Other fields should remain the same
    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_with_timestamp_overrides() -> None:
    """copy() should allow overriding timestamp fields."""
    original = Todo(id=1, text="buy milk", done=False)
    new_created = "2025-01-01T00:00:00+00:00"
    new_updated = "2025-01-02T00:00:00+00:00"

    copied = original.copy(created_at=new_created, updated_at=new_updated)

    # Timestamps should be updated
    assert copied.created_at == new_created
    assert copied.updated_at == new_updated

    # Other fields should remain the same
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
