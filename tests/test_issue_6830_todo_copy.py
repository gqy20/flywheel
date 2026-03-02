"""Tests for Todo.copy method (Issue #6830).

These tests verify that:
1. todo.copy() returns new Todo with identical field values
2. todo.copy(text='new') returns Todo with updated text but same id
3. Original todo is unchanged after copy operation
4. Copied todo has new updated_at timestamp
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_copy_returns_independent_instance() -> None:
    """copy() should return a new independent Todo instance."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Should be a different object
    assert copied is not original
    # Should have the same field values
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at


def test_copy_with_text_override() -> None:
    """copy(text='new') should return Todo with updated text but same id."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread")

    # Should have new text
    assert copied.text == "buy bread"
    # Should preserve other fields
    assert copied.id == original.id
    assert copied.done == original.done


def test_copy_with_done_override() -> None:
    """copy(done=True) should return Todo with updated done status."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(done=True)

    assert copied.done is True
    assert original.done is False  # original unchanged


def test_original_unchanged_after_copy_modification() -> None:
    """Original todo should be unchanged after copy modification."""
    original = Todo(id=1, text="original text", done=False)
    copied = original.copy(text="modified text")
    copied.mark_done()

    # Original should remain unchanged
    assert original.text == "original text"
    assert original.done is False


def test_copy_has_new_updated_at_timestamp() -> None:
    """Copied todo should have new updated_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    # Small delay to ensure timestamp difference
    time.sleep(0.001)
    copied = original.copy()

    # Updated_at should be different (newer)
    assert copied.updated_at != original.updated_at
    # But created_at should be preserved
    assert copied.created_at == original.created_at


def test_copy_with_multiple_overrides() -> None:
    """copy() should accept multiple field overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread", done=True, id=2)

    assert copied.id == 2
    assert copied.text == "buy bread"
    assert copied.done is True
    assert original.id == 1  # original unchanged
