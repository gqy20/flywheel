"""Tests for Todo.copy() method (Issue #4538).

These tests verify that:
1. todo.copy() returns a new Todo instance (different object)
2. todo.copy(text='new') returns a new instance with overridden text
3. copy() preserves the original created_at timestamp
4. copy() updates the updated_at timestamp automatically
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_returns_different_object() -> None:
    """todo.copy() should return a new Todo instance (not the same object)."""
    original = Todo(id=1, text="original task", done=False)
    copied = original.copy()

    # Should be different objects
    assert copied is not original
    # Should have same values
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_with_text_override() -> None:
    """todo.copy(text='new') should return a new instance with overridden text."""
    original = Todo(id=1, text="original task", done=False)
    copied = original.copy(text="new task")

    assert copied.text == "new task"
    assert original.text == "original task"  # Original unchanged
    assert copied.id == original.id
    assert copied.done == original.done


def test_todo_copy_with_done_override() -> None:
    """todo.copy(done=True) should return a new instance with done=True."""
    original = Todo(id=1, text="task", done=False)
    copied = original.copy(done=True)

    assert copied.done is True
    assert original.done is False  # Original unchanged


def test_todo_copy_with_id_override() -> None:
    """todo.copy(id=99) should allow overriding id field."""
    original = Todo(id=1, text="task", done=False)
    copied = original.copy(id=99)

    assert copied.id == 99
    assert original.id == 1  # Original unchanged


def test_todo_copy_with_multiple_overrides() -> None:
    """todo.copy() should support multiple field overrides."""
    original = Todo(id=1, text="original", done=False)
    copied = original.copy(id=2, text="new", done=True)

    assert copied.id == 2
    assert copied.text == "new"
    assert copied.done is True

    # Original unchanged
    assert original.id == 1
    assert original.text == "original"
    assert original.done is False


def test_todo_copy_preserves_created_at() -> None:
    """copy() should preserve the original created_at timestamp."""
    original = Todo(id=1, text="task", done=False)
    original_created_at = original.created_at

    copied = original.copy(text="new task")

    assert copied.created_at == original_created_at
    assert original.created_at == original_created_at


def test_todo_copy_updates_updated_at() -> None:
    """copy() should update the updated_at timestamp automatically."""
    original = Todo(id=1, text="task", done=False)
    original_updated_at = original.updated_at

    # Small delay to ensure different timestamp
    time.sleep(0.01)

    copied = original.copy(text="new task")

    # Copied should have newer updated_at
    assert copied.updated_at > original_updated_at
    # Original should remain unchanged
    assert original.updated_at == original_updated_at


def test_todo_copy_no_override_updates_updated_at() -> None:
    """copy() with no overrides should still update updated_at."""
    original = Todo(id=1, text="task", done=False)
    original_updated_at = original.updated_at

    time.sleep(0.01)

    copied = original.copy()

    assert copied.updated_at > original_updated_at


def test_todo_copy_empty_overrides() -> None:
    """todo.copy() with no arguments should return equivalent Todo."""
    original = Todo(id=1, text="task", done=True)
    copied = original.copy()

    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at
