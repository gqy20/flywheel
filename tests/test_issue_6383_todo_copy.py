"""Tests for Todo.copy() method (Issue #6383).

These tests verify that:
1. copy() returns a new Todo object with identical content but different identity
2. copy(text='new') returns a copy with modified text only
3. copy(done=True) returns a copy with done=True
4. Timestamps are preserved unless explicitly overridden
5. copy() supports multiple field overrides at once
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_copy_returns_new_object() -> None:
    """copy() should return a new Todo object with identical content but different identity."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    # Should be different objects (not the same reference)
    assert copy is not original
    # Should have identical content
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_copy_with_text_override() -> None:
    """copy(text='new') should return a copy with modified text only."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy(text="buy bread")

    # Original should be unchanged
    assert original.text == "buy milk"
    # Copy should have new text
    assert copy.text == "buy bread"
    # Other fields should remain the same
    assert copy.id == original.id
    assert copy.done == original.done
    assert copy.created_at == original.created_at


def test_copy_with_done_override() -> None:
    """copy(done=True) should return a copy with done=True."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(done=True)

    # Original should be unchanged
    assert original.done is False
    # Copy should have done=True
    assert copy.done is True
    # Other fields should remain the same
    assert copy.id == original.id
    assert copy.text == original.text


def test_copy_preserves_timestamps() -> None:
    """copy() should preserve created_at and updated_at unless explicitly overridden."""
    original = Todo(id=1, text="buy milk", done=False)
    original_created_at = original.created_at
    original_updated_at = original.updated_at

    copy = original.copy()

    # Timestamps should be preserved
    assert copy.created_at == original_created_at
    assert copy.updated_at == original_updated_at


def test_copy_with_multiple_overrides() -> None:
    """copy() should support multiple field overrides at once."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(text="buy bread", done=True)

    # Original should be unchanged
    assert original.text == "buy milk"
    assert original.done is False

    # Copy should have both overrides applied
    assert copy.text == "buy bread"
    assert copy.done is True
    # Non-overridden fields should remain the same
    assert copy.id == original.id
    assert copy.created_at == original.created_at


def test_copy_with_timestamp_override() -> None:
    """copy() should allow explicit timestamp overrides when provided."""
    original = Todo(id=1, text="buy milk", done=False)
    new_timestamp = "2024-01-01T00:00:00+00:00"

    copy = original.copy(updated_at=new_timestamp)

    # Original should be unchanged
    assert original.updated_at != new_timestamp
    # Copy should have the new timestamp
    assert copy.updated_at == new_timestamp
