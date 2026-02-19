"""Tests for Todo.edit() method (Issue #4497).

These tests verify that:
1. todo.edit(text='new text') updates text and updated_at
2. todo.edit(done=True) updates done and updated_at
3. todo.edit(text='x', done=True) updates both and updated_at
4. todo.edit() with no args does not update any field or updated_at
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_edit_updates_text() -> None:
    """todo.edit(text='new') should update text and updated_at."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    todo.edit(text="new text")

    assert todo.text == "new text"
    assert todo.updated_at != original_updated_at


def test_todo_edit_updates_done_to_true() -> None:
    """todo.edit(done=True) should update done and updated_at."""
    todo = Todo(id=1, text="task", done=False)
    original_updated_at = todo.updated_at

    todo.edit(done=True)

    assert todo.done is True
    assert todo.updated_at != original_updated_at


def test_todo_edit_updates_done_to_false() -> None:
    """todo.edit(done=False) should update done and updated_at."""
    todo = Todo(id=1, text="task", done=True)
    original_updated_at = todo.updated_at

    todo.edit(done=False)

    assert todo.done is False
    assert todo.updated_at != original_updated_at


def test_todo_edit_updates_both_fields() -> None:
    """todo.edit(text='a', done=True) should update both and updated_at."""
    todo = Todo(id=1, text="original", done=False)
    original_updated_at = todo.updated_at

    todo.edit(text="updated", done=True)

    assert todo.text == "updated"
    assert todo.done is True
    assert todo.updated_at != original_updated_at


def test_todo_edit_no_args_no_change() -> None:
    """todo.edit() with no args should not change any field or updated_at."""
    todo = Todo(id=1, text="original", done=True)
    original_updated_at = todo.updated_at

    todo.edit()

    assert todo.text == "original"
    assert todo.done is True
    assert todo.updated_at == original_updated_at


def test_todo_edit_validates_empty_text() -> None:
    """todo.edit(text='') should raise ValueError and not change state."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    try:
        todo.edit(text="")
        raise AssertionError("Expected ValueError for empty text")
    except ValueError as e:
        assert "empty" in str(e).lower()

    # State should remain unchanged
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_edit_strips_whitespace_from_text() -> None:
    """todo.edit(text='  padded  ') should strip whitespace."""
    todo = Todo(id=1, text="original")

    todo.edit(text="  padded  ")

    assert todo.text == "padded"
