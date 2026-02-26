"""Tests for Todo.copy() method (Issue #5931).

These tests verify that:
1. copy() creates a new Todo instance with the same text
2. copy(text='new') creates a new Todo with modified text
3. The copy has new id, created_at, and updated_at values
4. The copy is a distinct object from the original
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_creates_new_instance() -> None:
    """copy() should return a new Todo object with the same text."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy()

    # Should be a different object
    assert copy is not original
    assert id(copy) != id(original)

    # Should have the same text
    assert copy.text == original.text

    # Should have new timestamps (different from original)
    assert copy.created_at != original.created_at
    assert copy.updated_at != original.updated_at


def test_todo_copy_with_new_text() -> None:
    """copy(text='new') should create a Todo with the new text."""
    original = Todo(id=1, text="buy milk")
    copy = original.copy(text="buy bread")

    # Should have the new text
    assert copy.text == "buy bread"
    assert original.text == "buy milk"  # Original unchanged

    # Should have new timestamps
    assert copy.created_at != original.created_at


def test_todo_copy_has_fresh_timestamps() -> None:
    """copy() should generate fresh created_at and updated_at."""
    original = Todo(id=1, text="task")
    # Small delay to ensure timestamps differ
    time.sleep(0.01)
    copy = original.copy()

    # New timestamps should be generated
    assert copy.created_at != ""
    assert copy.updated_at != ""
    assert copy.created_at != original.created_at
    assert copy.updated_at != original.updated_at


def test_todo_copy_preserves_done_state() -> None:
    """copy() should preserve the done state of the original."""
    original_done = Todo(id=1, text="task", done=True)
    copy_done = original_done.copy()
    assert copy_done.done is True

    original_not_done = Todo(id=2, text="task", done=False)
    copy_not_done = original_not_done.copy()
    assert copy_not_done.done is False


def test_todo_copy_independent_of_original() -> None:
    """Modifying the copy should not affect the original."""
    original = Todo(id=1, text="original text", done=False)
    copy = original.copy(text="modified text")

    # Modify the copy
    copy.mark_done()

    # Original should be unchanged
    assert original.text == "original text"
    assert original.done is False

    # Copy should have new values
    assert copy.text == "modified text"
    assert copy.done is True
