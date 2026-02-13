"""Tests for Todo.copy() method (Issue #2988).

These tests verify that:
1. todo.copy() returns an independent copy
2. todo.copy(**kwargs) allows overriding specific fields
3. copy() automatically updates updated_at timestamp
4. Original object is not affected by copy operations
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
    # Should have same values
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at


def test_todo_copy_updates_text() -> None:
    """copy(text='new') should return a copy with updated text."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread")

    # Original should be unchanged
    assert original.text == "buy milk"
    # Copy should have new text
    assert copied.text == "buy bread"
    # Other fields should be preserved
    assert copied.id == original.id
    assert copied.done == original.done


def test_todo_copy_updates_done_status() -> None:
    """copy(done=True) should return a copy with updated done status."""
    original = Todo(id=1, text="task", done=False)
    copied = original.copy(done=True)

    # Original should remain undone
    assert original.done is False
    # Copy should be done
    assert copied.done is True
    # Other fields should be preserved
    assert copied.text == original.text


def test_todo_copy_updates_updated_at_timestamp() -> None:
    """copy() should automatically update updated_at timestamp."""
    original = Todo(id=1, text="task", done=False)
    original_updated_at = original.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    copied = original.copy()

    # Copy should have a newer updated_at
    assert copied.updated_at != original_updated_at
    # Original's updated_at should be unchanged
    assert original.updated_at == original_updated_at


def test_todo_copy_preserves_created_at() -> None:
    """copy() should preserve created_at from original."""
    original = Todo(id=1, text="task", done=False)
    original_created_at = original.created_at

    copied = original.copy(text="new task")

    # created_at should be the same
    assert copied.created_at == original_created_at
    assert original.created_at == original_created_at


def test_todo_copy_can_update_multiple_fields() -> None:
    """copy() should allow updating multiple fields at once."""
    original = Todo(id=1, text="old", done=False)
    copied = original.copy(text="new", done=True)

    assert copied.text == "new"
    assert copied.done is True
    # Original unchanged
    assert original.text == "old"
    assert original.done is False


def test_todo_copy_with_no_args_returns_fresh_timestamp() -> None:
    """copy() with no args should still update updated_at."""
    original = Todo(id=1, text="task")
    time.sleep(0.01)
    copied = original.copy()

    # All values should be same except updated_at
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at
    # But updated_at should be different
    assert copied.updated_at != original.updated_at


def test_todo_copy_explicit_updated_at_override() -> None:
    """copy(updated_at=...) should allow explicit override if needed."""
    original = Todo(id=1, text="task")
    explicit_time = "2024-01-01T00:00:00+00:00"
    copied = original.copy(updated_at=explicit_time)

    assert copied.updated_at == explicit_time
    # Original unchanged
    assert original.updated_at != explicit_time


def test_todo_copy_original_unchanged_after_copy_modification() -> None:
    """Modifying copy should not affect original."""
    original = Todo(id=1, text="original", done=False)
    copied = original.copy(text="modified")

    # Modify copy via method
    copied.mark_done()

    # Original should still have original values
    assert original.text == "original"
    assert original.done is False
