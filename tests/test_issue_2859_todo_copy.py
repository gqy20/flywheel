"""Tests for Todo.copy() method (Issue #2859).

These tests verify that:
1. copy() creates an independent Todo instance with same values
2. copy(text=...) overrides the text field
3. copy(done=...) overrides the done field
4. Original todo is unchanged after copy operations
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_copy_creates_independent_instance() -> None:
    """copy() should return a new Todo instance with same values."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Should be a different object
    assert copied is not original

    # Should have same values
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done


def test_copy_override_text() -> None:
    """copy(text='new') should return new Todo with updated text."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread")

    # Should have new text
    assert copied.text == "buy bread"

    # Original should be unchanged
    assert original.text == "buy milk"

    # Other fields should match
    assert copied.id == original.id
    assert copied.done == original.done


def test_copy_override_done() -> None:
    """copy(done=True) should return new Todo with updated done status."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(done=True)

    # Should have new done status
    assert copied.done is True

    # Original should be unchanged
    assert original.done is False

    # Other fields should match
    assert copied.id == original.id
    assert copied.text == original.text


def test_copy_override_both_text_and_done() -> None:
    """copy() with multiple overrides should update all specified fields."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread", done=True)

    # Should have all new values
    assert copied.text == "buy bread"
    assert copied.done is True
    assert copied.id == original.id

    # Original should be unchanged
    assert original.text == "buy milk"
    assert original.done is False


def test_copy_with_timestamps() -> None:
    """copy() should create independent instance with copied timestamps."""
    original = Todo(id=1, text="buy milk", done=False)
    original_created = original.created_at
    original_updated = original.updated_at

    copied = original.copy()

    # Timestamps should be copied (not modified unless fields change)
    assert copied.created_at == original_created
    assert copied.updated_at == original_updated


def test_copy_empty_text_raises_error() -> None:
    """copy(text='') should raise ValueError (same as rename())."""
    original = Todo(id=1, text="buy milk", done=False)

    with pytest.raises(ValueError, match="text cannot be empty"):
        original.copy(text="")


def test_copy_whitespace_only_text_gets_stripped() -> None:
    """copy(text='  ') should raise ValueError after stripping."""
    original = Todo(id=1, text="buy milk", done=False)

    with pytest.raises(ValueError, match="text cannot be empty"):
        original.copy(text="   ")


def test_original_unchanged_after_copy() -> None:
    """Original todo should remain unchanged after any copy operation."""
    original = Todo(id=1, text="buy milk", done=False)
    original_text = original.text
    original_done = original.done
    original_created = original.created_at
    original_updated = original.updated_at

    # Various copy operations
    _ = original.copy()
    _ = original.copy(text="new text")
    _ = original.copy(done=True)
    _ = original.copy(text="modified", done=True)

    # Original should never change
    assert original.text == original_text
    assert original.done == original_done
    assert original.created_at == original_created
    assert original.updated_at == original_updated
