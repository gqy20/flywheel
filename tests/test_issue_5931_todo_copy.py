"""Tests for Todo.copy() method (Issue #5931).

These tests verify that:
1. todo.copy() returns a new Todo object with the same text
2. todo.copy(text='new') returns a new Todo object with modified text
3. The copy has new created_at and updated_at timestamps
4. The copy is a different object (id() is different)
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_creates_new_instance() -> None:
    """copy() should return a new Todo object with same text."""
    original = Todo(id=1, text="original task", done=False)
    copy = original.copy()

    # Should be a different object
    assert copy is not original
    assert id(copy) != id(original)

    # Should have the same text
    assert copy.text == original.text

    # Should have the same done status
    assert copy.done == original.done


def test_todo_copy_with_new_text() -> None:
    """copy(text='new') should return a new Todo with modified text."""
    original = Todo(id=1, text="original task", done=False)
    copy = original.copy(text="new task")

    # Should be a different object
    assert copy is not original

    # Should have the new text
    assert copy.text == "new task"
    assert original.text == "original task"  # Original unchanged


def test_todo_copy_has_new_timestamps() -> None:
    """copy() should have new created_at and updated_at timestamps."""
    original = Todo(id=1, text="task")
    # Small delay to ensure different timestamps
    time.sleep(0.01)
    copy = original.copy()

    # Copy should have different (newer) timestamps
    assert copy.created_at != original.created_at
    assert copy.updated_at != original.updated_at

    # Copy timestamps should be close to now
    assert copy.created_at == copy.updated_at


def test_todo_copy_preserves_done_status() -> None:
    """copy() should preserve the done status."""
    # Test with done=True
    original_done = Todo(id=1, text="completed task", done=True)
    copy_done = original_done.copy()
    assert copy_done.done is True

    # Test with done=False (default)
    original_undone = Todo(id=2, text="incomplete task", done=False)
    copy_undone = original_undone.copy()
    assert copy_undone.done is False


def test_todo_copy_with_empty_text_uses_original() -> None:
    """copy(text=None) should use original text."""
    original = Todo(id=1, text="original task")
    copy = original.copy(text=None)

    assert copy.text == original.text
    assert copy is not original


def test_todo_copy_from_completed_todo() -> None:
    """copy() from a completed todo should work correctly."""
    original = Todo(id=1, text="completed task", done=True)
    original.created_at = "2024-01-01T00:00:00+00:00"
    original.updated_at = "2024-01-02T00:00:00+00:00"

    copy = original.copy()

    # Should preserve done status
    assert copy.done is True
    # But have new timestamps
    assert copy.created_at != "2024-01-01T00:00:00+00:00"
    assert copy.updated_at != "2024-01-02T00:00:00+00:00"
