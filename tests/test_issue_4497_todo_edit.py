"""Tests for issue #4497: Todo.edit() method for partial updates."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_edit_updates_text_only() -> None:
    """todo.edit(text='new') should update text and updated_at."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    todo.edit(text="new text")

    assert todo.text == "new text"
    assert todo.done is False  # unchanged
    assert todo.updated_at > original_updated_at


def test_todo_edit_updates_done_only() -> None:
    """todo.edit(done=True) should update done and updated_at."""
    todo = Todo(id=1, text="task", done=False)
    original_updated_at = todo.updated_at

    todo.edit(done=True)

    assert todo.done is True
    assert todo.text == "task"  # unchanged
    assert todo.updated_at > original_updated_at


def test_todo_edit_updates_both_fields() -> None:
    """todo.edit(text='a', done=True) should update both and updated_at."""
    todo = Todo(id=1, text="original", done=False)
    original_updated_at = todo.updated_at

    todo.edit(text="updated", done=True)

    assert todo.text == "updated"
    assert todo.done is True
    assert todo.updated_at > original_updated_at


def test_todo_edit_no_args_no_change() -> None:
    """todo.edit() with no args should not change any field or updated_at."""
    todo = Todo(id=1, text="original", done=False)
    original_updated_at = todo.updated_at

    todo.edit()

    assert todo.text == "original"
    assert todo.done is False
    assert todo.updated_at == original_updated_at


def test_todo_edit_strips_text_whitespace() -> None:
    """todo.edit() should strip whitespace from text like rename()."""
    todo = Todo(id=1, text="original")

    todo.edit(text="  padded  ")

    assert todo.text == "padded"


def test_todo_edit_rejects_empty_text() -> None:
    """todo.edit() should reject empty text after strip."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    try:
        todo.edit(text="")
        raise AssertionError("Expected ValueError for empty text")
    except ValueError as e:
        assert "empty" in str(e).lower()

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_edit_rejects_whitespace_only_text() -> None:
    """todo.edit() should reject whitespace-only text."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    try:
        todo.edit(text="   ")
        raise AssertionError("Expected ValueError for whitespace-only text")
    except ValueError as e:
        assert "empty" in str(e).lower()

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_edit_can_set_done_to_false() -> None:
    """todo.edit(done=False) should set done to False."""
    todo = Todo(id=1, text="task", done=True)
    original_updated_at = todo.updated_at

    todo.edit(done=False)

    assert todo.done is False
    assert todo.updated_at > original_updated_at


def test_todo_edit_text_none_done_none_no_change() -> None:
    """Explicitly passing None for both args should not change anything."""
    todo = Todo(id=1, text="original", done=True)
    original_updated_at = todo.updated_at

    todo.edit(text=None, done=None)

    assert todo.text == "original"
    assert todo.done is True
    assert todo.updated_at == original_updated_at
