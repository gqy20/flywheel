"""Tests for Todo.copy_with() method (Issue #3709).

These tests verify that:
1. copy_with() returns a new Todo instance (does not modify original)
2. copy_with() supports immutable-style updates for text, done, updated_at
3. created_at is preserved from the original instance
4. updated_at is automatically refreshed unless explicitly provided
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_copy_with_returns_new_instance() -> None:
    """copy_with() should return a new Todo instance, not modify original."""
    original = Todo(id=1, text="original task", done=False)
    copied = original.copy_with(done=True)

    assert copied is not original
    assert isinstance(copied, Todo)


def test_copy_with_done_true() -> None:
    """copy_with(done=True) should update the done field."""
    original = Todo(id=1, text="task", done=False)
    copied = original.copy_with(done=True)

    assert copied.done is True
    assert original.done is False


def test_copy_with_text() -> None:
    """copy_with(text='new') should update the text field."""
    original = Todo(id=1, text="old text", done=False)
    copied = original.copy_with(text="new text")

    assert copied.text == "new text"
    assert original.text == "old text"


def test_copy_with_original_unchanged() -> None:
    """Original instance should remain unchanged after copy_with."""
    original = Todo(id=1, text="unchanged", done=False)
    original_created = original.created_at
    original_updated = original.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    original.copy_with(text="changed", done=True)

    assert original.text == "unchanged"
    assert original.done is False
    assert original.created_at == original_created
    assert original.updated_at == original_updated


def test_copy_with_preserves_created_at() -> None:
    """created_at should be preserved from original instance."""
    original = Todo(id=1, text="task", done=False)

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    copied = original.copy_with(done=True)

    assert copied.created_at == original.created_at


def test_copy_with_updates_updated_at() -> None:
    """updated_at should be refreshed to new timestamp."""
    original = Todo(id=1, text="task", done=False)
    original_updated = original.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    copied = original.copy_with(done=True)

    assert copied.updated_at != original_updated


def test_copy_with_no_args() -> None:
    """copy_with() with no args should return a copy with same values."""
    original = Todo(id=1, text="task", done=True)
    copied = original.copy_with()

    assert copied is not original
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at
    # updated_at will be refreshed even with no args


def test_copy_with_multiple_fields() -> None:
    """copy_with() should support updating multiple fields at once."""
    original = Todo(id=1, text="old", done=False)
    copied = original.copy_with(text="new", done=True)

    assert copied.text == "new"
    assert copied.done is True
    assert original.text == "old"
    assert original.done is False
