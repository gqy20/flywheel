"""Tests for Todo.copy_with method (Issue #4218).

These tests verify that:
1. copy_with returns a new Todo instance with updated fields
2. Original Todo instance is not modified
3. New instance's updated_at is automatically updated
4. Any field (text, done) can be updated
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_copy_with_updates_done_field() -> None:
    """copy_with(done=True) should return new Todo with done=True."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy_with(done=True)

    assert copy.done is True
    assert copy.id == original.id
    assert copy.text == original.text


def test_copy_with_preserves_original() -> None:
    """Original Todo should remain unchanged after copy_with."""
    original = Todo(id=1, text="buy milk", done=False)
    original_updated_at = original.updated_at

    copy = original.copy_with(done=True)

    # Original should not be modified
    assert original.done is False
    assert original.updated_at == original_updated_at
    # Copy should have new values
    assert copy.done is True


def test_copy_with_updates_updated_at() -> None:
    """New instance's updated_at should be newer than original."""
    original = Todo(id=1, text="buy milk", done=False)
    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    copy = original.copy_with(done=True)

    assert copy.updated_at > original.updated_at


def test_copy_with_updates_text() -> None:
    """copy_with(text='new') should return Todo with updated text."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy_with(text="buy bread")

    assert copy.text == "buy bread"
    assert original.text == "buy milk"


def test_copy_with_updates_multiple_fields() -> None:
    """copy_with should support updating multiple fields at once."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy_with(text="buy bread", done=True)

    assert copy.text == "buy bread"
    assert copy.done is True
    assert original.text == "buy milk"
    assert original.done is False


def test_copy_with_no_changes_returns_equal_todo() -> None:
    """copy_with() with no args should return a copy with updated timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    time.sleep(0.01)
    copy = original.copy_with()

    # Same values except timestamps
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    # But updated_at should be newer
    assert copy.updated_at > original.updated_at
    # And it should be a different object
    assert copy is not original
