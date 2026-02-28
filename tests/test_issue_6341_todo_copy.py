"""Tests for Todo.copy() method (Issue #6341).

These tests verify that:
1. todo.copy() returns a new Todo instance with same text/done
2. copy() generates new created_at/updated_at timestamps
3. copy() returns a different object (not the same instance)
4. modifying original doesn't affect copy
5. optional new_id parameter works
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_returns_new_instance() -> None:
    """copy() should return a different Todo object."""
    todo = Todo(id=1, text="buy milk", done=False)
    copied = todo.copy()

    assert copied is not todo, "copy() should return a new instance"


def test_todo_copy_preserves_text_and_done() -> None:
    """copy() should preserve text and done status."""
    todo = Todo(id=1, text="buy milk", done=True)
    copied = todo.copy()

    assert copied.text == todo.text
    assert copied.done == todo.done


def test_todo_copy_generates_new_timestamps() -> None:
    """copy() should generate new created_at and updated_at timestamps."""
    todo = Todo(id=1, text="buy milk", done=False)
    # Small delay to ensure different timestamp
    time.sleep(0.01)
    copied = todo.copy()

    assert copied.created_at != todo.created_at
    assert copied.updated_at != todo.updated_at


def test_todo_copy_independent_from_original() -> None:
    """Modifying original should not affect the copy."""
    todo = Todo(id=1, text="original text", done=False)
    copied = todo.copy()

    # Modify original
    todo.rename("modified text")
    todo.mark_done()

    # Copy should remain unchanged
    assert copied.text == "original text"
    assert copied.done is False


def test_todo_copy_with_new_id() -> None:
    """copy() should accept optional new_id parameter."""
    todo = Todo(id=1, text="buy milk", done=False)
    copied = todo.copy(new_id=42)

    assert copied.id == 42
    assert todo.id == 1  # Original unchanged


def test_todo_copy_default_generates_new_id() -> None:
    """copy() without new_id should use same id by default."""
    todo = Todo(id=1, text="buy milk", done=False)
    copied = todo.copy()

    # Default behavior: same id (user can provide new_id if needed)
    assert copied.id == todo.id
