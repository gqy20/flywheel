"""Tests for Todo.copy_with method (Issue #4218).

These tests verify that:
1. copy_with returns a new Todo instance without modifying the original
2. copy_with supports updating any field (text, done)
3. The new instance's updated_at is automatically updated
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_copy_with_updates_done_field() -> None:
    """copy_with(done=True) should return a new Todo instance with done=True."""
    original = Todo(id=1, text="buy milk", done=False)
    original_updated_at = original.updated_at

    # Small delay to ensure updated_at differs
    time.sleep(0.01)

    copy = original.copy_with(done=True)

    # The copy should have done=True
    assert copy.done is True
    # The original should remain unchanged
    assert original.done is False
    # The copy should have a newer updated_at
    assert copy.updated_at > original_updated_at
    # The original's updated_at should remain unchanged
    assert original.updated_at == original_updated_at


def test_copy_with_updates_text_field() -> None:
    """copy_with(text='new text') should return a new Todo with updated text."""
    original = Todo(id=1, text="old text", done=False)
    original_updated_at = original.updated_at

    time.sleep(0.01)

    copy = original.copy_with(text="new text")

    # The copy should have the new text
    assert copy.text == "new text"
    # The original should remain unchanged
    assert original.text == "old text"
    # The copy should have a newer updated_at
    assert copy.updated_at > original_updated_at


def test_copy_with_updates_multiple_fields() -> None:
    """copy_with should support updating multiple fields at once."""
    original = Todo(id=1, text="old text", done=False)

    copy = original.copy_with(text="new text", done=True)

    assert copy.text == "new text"
    assert copy.done is True
    # Original unchanged
    assert original.text == "old text"
    assert original.done is False


def test_copy_with_preserves_other_fields() -> None:
    """copy_with should preserve fields not explicitly changed."""
    original = Todo(id=1, text="task", done=False)

    copy = original.copy_with(done=True)

    # id and text should be preserved
    assert copy.id == original.id
    assert copy.text == original.text
    # created_at should be preserved
    assert copy.created_at == original.created_at


def test_copy_with_no_changes_returns_equivalent_copy() -> None:
    """copy_with() with no arguments should return a copy with fresh updated_at."""
    original = Todo(id=1, text="task", done=False)
    original_updated_at = original.updated_at

    time.sleep(0.01)

    copy = original.copy_with()

    # All values should be the same except updated_at
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    # updated_at should be fresh
    assert copy.updated_at > original_updated_at
