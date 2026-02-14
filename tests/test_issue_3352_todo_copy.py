"""Tests for Todo.copy method (Issue #3352).

These tests verify that:
1. todo.copy() returns a new Todo object with same values
2. todo.copy(text='new') returns a new Todo with modified text
3. todo.copy supports overriding all fields
4. The returned copy is a different object (not the same reference)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_equal_values() -> None:
    """todo.copy() should return a new Todo with same values."""
    original = Todo(id=1, text="buy milk")
    copy = original.copy()

    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_todo_copy_is_new_object() -> None:
    """todo.copy() should return a different object."""
    original = Todo(id=1, text="buy milk")
    copy = original.copy()

    assert copy is not original


def test_todo_copy_with_text_override() -> None:
    """todo.copy(text='new') should return Todo with modified text only."""
    original = Todo(id=1, text="buy milk")
    copy = original.copy(text="buy bread")

    assert copy.text == "buy bread"
    assert copy.id == original.id
    assert copy.done == original.done


def test_todo_copy_with_multiple_overrides() -> None:
    """todo.copy() should allow overriding multiple fields."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(id=2, text="buy bread", done=True)

    assert copy.id == 2
    assert copy.text == "buy bread"
    assert copy.done is True
    # Timestamps should be preserved from original
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_todo_copy_preserves_done_status() -> None:
    """todo.copy() should preserve the done status."""
    done_todo = Todo(id=1, text="done task", done=True)
    copy = done_todo.copy()

    assert copy.done is True

    undone_todo = Todo(id=2, text="undone task", done=False)
    copy2 = undone_todo.copy()

    assert copy2.done is False


def test_todo_copy_overrides_done() -> None:
    """todo.copy(done=True/False) should allow changing done status."""
    original = Todo(id=1, text="task", done=False)
    copy = original.copy(done=True)

    assert copy.done is True
    assert original.done is False  # Original unchanged


def test_todo_copy_with_timestamp_overrides() -> None:
    """todo.copy() should allow overriding timestamps."""
    original = Todo(id=1, text="task")
    new_time = "2024-01-01T00:00:00+00:00"
    copy = original.copy(created_at=new_time, updated_at=new_time)

    assert copy.created_at == new_time
    assert copy.updated_at == new_time


def test_todo_copy_no_side_effects() -> None:
    """Modifying the copy should not affect the original."""
    original = Todo(id=1, text="original text", done=False)
    copy = original.copy(text="new text")

    # Modify the copy
    copy.mark_done()

    # Original should be unchanged
    assert original.text == "original text"
    assert original.done is False
