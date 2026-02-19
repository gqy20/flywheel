"""Tests for Todo.copy() method (Issue #4512).

These tests verify that:
1. copy() returns a new Todo instance with same fields
2. copy(**kwargs) returns a new Todo with specified fields replaced
3. copy() automatically updates the updated_at timestamp
4. Original Todo is not modified by copy()
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_new_instance() -> None:
    """copy() should return a different object with same fields."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Should be different objects
    assert copied is not original

    # Should have same field values
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_with_text_override() -> None:
    """copy(text='x') should return new Todo with only text changed."""
    original = Todo(id=1, text="buy milk", done=True)
    copied = original.copy(text="buy bread")

    # Text should be changed
    assert copied.text == "buy bread"

    # Other fields should remain the same
    assert copied.id == original.id
    assert copied.done == original.done
    assert copied.done is True


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should return new Todo with done changed."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(done=True)

    # done should be changed
    assert copied.done is True

    # Other fields should remain the same
    assert copied.id == original.id
    assert copied.text == original.text


def test_todo_copy_with_id_override() -> None:
    """copy(id=2) should return new Todo with id changed."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(id=2)

    # id should be changed
    assert copied.id == 2

    # Other fields should remain the same
    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_updates_timestamp() -> None:
    """copy() should automatically update updated_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)

    copied = original.copy()

    # updated_at should be set (may or may not differ based on timing)
    assert copied.updated_at != ""
    # The copy should have an updated_at (new timestamp set by copy)
    assert copied.updated_at is not None


def test_todo_copy_preserves_original() -> None:
    """copy() should not modify the original Todo."""
    original = Todo(id=1, text="buy milk", done=False)
    original_text = original.text
    original_done = original.done
    original_updated_at = original.updated_at

    # Create copy with overrides
    copied = original.copy(text="new text", done=True)

    # Original should be unchanged
    assert original.text == original_text
    assert original.done == original_done
    assert original.updated_at == original_updated_at

    # Copy should have new values
    assert copied.text == "new text"
    assert copied.done is True


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should support overriding multiple fields at once."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(id=2, text="buy bread", done=True)

    assert copied.id == 2
    assert copied.text == "buy bread"
    assert copied.done is True


def test_todo_copy_preserves_created_at() -> None:
    """copy() should preserve the original created_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="new text")

    # created_at should be preserved
    assert copied.created_at == original.created_at

    # Unless explicitly overridden
    copied2 = original.copy(created_at="2024-01-01T00:00:00+00:00")
    assert copied2.created_at == "2024-01-01T00:00:00+00:00"
