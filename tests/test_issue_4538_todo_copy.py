"""Tests for Todo.copy() method (Issue #4538).

These tests verify that:
1. todo.copy() returns a different object with same attributes
2. todo.copy(text='new') returns a new instance with updated text
3. copy() preserves the original created_at timestamp
4. copy() updates the updated_at timestamp
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_returns_different_object() -> None:
    """copy() should return a new Todo instance (not the same object)."""
    todo = Todo(id=1, text="original", done=False)
    copied = todo.copy()

    # Should be different objects
    assert copied is not todo
    # But should have the same attributes
    assert copied.id == todo.id
    assert copied.text == todo.text
    assert copied.done == todo.done


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should return a new instance with updated text."""
    todo = Todo(id=1, text="original", done=False)
    copied = todo.copy(text="new text")

    assert copied.text == "new text"
    # Other attributes should remain unchanged
    assert copied.id == todo.id
    assert copied.done == todo.done


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should return a new instance with updated done status."""
    todo = Todo(id=1, text="task", done=False)
    copied = todo.copy(done=True)

    assert copied.done is True
    # Original should be unchanged
    assert todo.done is False


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should support multiple field overrides at once."""
    todo = Todo(id=1, text="original", done=False)
    copied = todo.copy(text="new text", done=True)

    assert copied.text == "new text"
    assert copied.done is True
    assert copied.id == todo.id  # id should remain unchanged


def test_todo_copy_preserves_created_at() -> None:
    """copy() should preserve the original created_at timestamp."""
    todo = Todo(id=1, text="task", done=False)
    original_created_at = todo.created_at

    copied = todo.copy(text="modified")

    # created_at should be preserved
    assert copied.created_at == original_created_at


def test_todo_copy_updates_updated_at() -> None:
    """copy() should update the updated_at timestamp."""
    todo = Todo(id=1, text="task", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    copied = todo.copy(text="modified")

    # updated_at should be newer than the original
    assert copied.updated_at > original_updated_at


def test_todo_copy_with_id_override() -> None:
    """copy() should allow overriding id field."""
    todo = Todo(id=1, text="task", done=False)
    copied = todo.copy(id=999)

    assert copied.id == 999
    assert todo.id == 1  # Original unchanged


def test_todo_copy_no_side_effects_on_original() -> None:
    """copy() should not modify the original Todo instance."""
    todo = Todo(id=1, text="original", done=False)
    original_text = todo.text
    original_done = todo.done
    original_created_at = todo.created_at
    original_updated_at = todo.updated_at

    # Perform copy with overrides
    _copied = todo.copy(text="new text", done=True, id=999)

    # Original should remain unchanged
    assert todo.text == original_text
    assert todo.done == original_done
    assert todo.created_at == original_created_at
    assert todo.updated_at == original_updated_at
