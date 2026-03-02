"""Tests for Todo.copy() method (Issue #6830).

These tests verify that:
1. todo.copy() returns new Todo with identical field values
2. todo.copy(text='new') returns Todo with updated text but same id
3. Original todo is unchanged after copy operation
4. Copied todo has new updated_at timestamp
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_returns_independent_instance() -> None:
    """copy() should return a new independent Todo instance."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Should be a different object
    assert copied is not original
    # Should have the same field values
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should return Todo with updated text but same id."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread")

    # Should have same id
    assert copied.id == original.id
    # Should have new text
    assert copied.text == "buy bread"
    # Original should be unchanged
    assert original.text == "buy milk"


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should return Todo with updated done status."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(done=True)

    # Should have same id and text
    assert copied.id == original.id
    assert copied.text == original.text
    # Should have new done status
    assert copied.done is True
    # Original should be unchanged
    assert original.done is False


def test_todo_copy_original_unchanged_after_modification() -> None:
    """Original todo should be unchanged after copy modification."""
    original = Todo(id=1, text="buy milk", done=False)
    original_created = original.created_at
    original_updated = original.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    copied = original.copy(text="buy bread")
    copied.mark_done()

    # Original should be unchanged
    assert original.text == "buy milk"
    assert original.done is False
    assert original.created_at == original_created
    assert original.updated_at == original_updated


def test_todo_copy_has_new_updated_at_timestamp() -> None:
    """Copied todo should have a new updated_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    original_updated = original.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    copied = original.copy()

    # Copied should have new updated_at
    assert copied.updated_at != original_updated
    # But same created_at
    assert copied.created_at == original.created_at


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should accept multiple field overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread", done=True)

    assert copied.id == 1
    assert copied.text == "buy bread"
    assert copied.done is True


def test_todo_copy_preserves_created_at() -> None:
    """copy() should preserve the original created_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="new text")

    # created_at should be the same
    assert copied.created_at == original.created_at
