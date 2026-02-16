"""Tests for Todo.copy_with() method (Issue #3709).

These tests verify that:
1. copy_with() returns a new Todo instance
2. The original instance remains unchanged
3. created_at is preserved from the original
4. All fields can be overridden via copy_with()
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_copy_with_returns_new_instance() -> None:
    """copy_with() should return a new Todo instance."""
    original = Todo(id=1, text="original task")
    copied = original.copy_with(done=True)

    assert copied is not original
    assert isinstance(copied, Todo)


def test_copy_with_preserves_created_at() -> None:
    """copy_with() should preserve created_at from the original instance."""
    original = Todo(id=1, text="task")
    original_created = original.created_at

    # Small delay to ensure timestamps would differ
    time.sleep(0.01)

    copied = original.copy_with(done=True)

    assert copied.created_at == original_created


def test_copy_with_original_unchanged() -> None:
    """copy_with() should not modify the original instance."""
    original = Todo(id=1, text="original task", done=False)
    original_created = original.created_at
    original_updated = original.updated_at

    time.sleep(0.01)

    original.copy_with(done=True, text="modified task")

    # Original should remain unchanged
    assert original.text == "original task"
    assert original.done is False
    assert original.created_at == original_created
    assert original.updated_at == original_updated


def test_copy_with_overrides_done() -> None:
    """copy_with() should allow overriding the done field."""
    original = Todo(id=1, text="task", done=False)
    copied = original.copy_with(done=True)

    assert copied.done is True
    assert original.done is False


def test_copy_with_overrides_text() -> None:
    """copy_with() should allow overriding the text field."""
    original = Todo(id=1, text="old text")
    copied = original.copy_with(text="new text")

    assert copied.text == "new text"
    assert original.text == "old text"


def test_copy_with_overrides_updated_at() -> None:
    """copy_with() should allow overriding the updated_at field."""
    original = Todo(id=1, text="task")
    original_updated = original.updated_at

    time.sleep(0.01)

    # By default, copy_with should update the updated_at timestamp
    copied = original.copy_with(done=True)

    # The copied todo should have a different updated_at
    assert copied.updated_at != original_updated


def test_copy_with_updates_updated_at_automatically() -> None:
    """copy_with() should update updated_at when any field changes."""
    original = Todo(id=1, text="task")
    original_updated = original.updated_at

    time.sleep(0.01)

    copied = original.copy_with(text="modified")

    assert copied.updated_at != original_updated
    assert original.updated_at == original_updated


def test_copy_with_no_args_returns_copy() -> None:
    """copy_with() with no args should return a copy of the todo."""
    original = Todo(id=1, text="task", done=True)
    copied = original.copy_with()

    assert copied is not original
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at


def test_copy_with_all_fields() -> None:
    """copy_with() should allow overriding all fields."""
    original = Todo(id=1, text="original", done=False)
    copied = original.copy_with(id=2, text="copied", done=True)

    assert copied.id == 2
    assert copied.text == "copied"
    assert copied.done is True
    # created_at should still be preserved
    assert copied.created_at == original.created_at
