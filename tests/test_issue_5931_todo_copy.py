"""Tests for Todo.copy() method (Issue #5931).

These tests verify that:
1. copy() returns a new Todo object with same text
2. copy(text='new') returns a new Todo with modified text
3. copy creates new timestamps (created_at, updated_at)
4. copy returns a different object (id() is different)
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_creates_new_instance() -> None:
    """copy() should return a new Todo object with same text."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    # Should be different objects
    assert copy is not original
    assert id(copy) != id(original)

    # Text should be the same
    assert copy.text == original.text

    # New timestamps should be generated
    assert copy.created_at != original.created_at
    assert copy.updated_at != original.updated_at


def test_todo_copy_with_new_text() -> None:
    """copy(text='new') should return a new Todo with modified text."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(text="buy bread")

    # Should be different objects
    assert copy is not original

    # Text should be the new value
    assert copy.text == "buy bread"
    assert original.text == "buy milk"  # Original unchanged


def test_todo_copy_resets_done_state() -> None:
    """copy() should create a fresh todo with done=False."""
    original = Todo(id=1, text="completed task", done=True)
    copy = original.copy()

    # Copy should start as not done
    assert copy.done is False
    assert original.done is True  # Original unchanged


def test_todo_copy_preserves_text_when_no_arg() -> None:
    """copy() without arguments should preserve original text."""
    original = Todo(id=1, text="some task")
    copy = original.copy()

    assert copy.text == "some task"


def test_todo_copy_new_timestamps() -> None:
    """copy() should generate new timestamps."""
    original = Todo(id=1, text="task")
    time.sleep(0.01)  # Small delay to ensure different timestamps

    copy = original.copy()

    # Timestamps should be newer in copy
    assert copy.created_at > original.created_at
    assert copy.updated_at > original.updated_at
