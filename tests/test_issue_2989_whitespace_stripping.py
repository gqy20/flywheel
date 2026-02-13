"""Tests for Issue #2989: whitespace stripping consistency.

These tests verify that Todo.__init__, Todo.rename(), and TodoApp.add()
all consistently strip whitespace from todo text.

The issue was that Todo.rename() and TodoApp.add() strip whitespace,
but Todo.__init__ did not, creating inconsistent behavior when Todo
is instantiated directly.
"""

from __future__ import annotations

from flywheel.cli import TodoApp
from flywheel.todo import Todo


def test_todo_init_strips_whitespace() -> None:
    """Todo.__init__ should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  hello world  ")

    # Should strip whitespace for consistency with rename() and TodoApp.add()
    assert todo.text == "hello world"


def test_todo_rename_strips_whitespace() -> None:
    """Todo.rename() should strip leading/trailing whitespace (existing behavior)."""
    todo = Todo(id=1, text="original")
    todo.rename("  renamed with spaces  ")

    assert todo.text == "renamed with spaces"


def test_todoapp_add_strips_whitespace() -> None:
    """TodoApp.add() should strip leading/trailing whitespace (existing behavior)."""
    app = TodoApp(db_path=":memory:")
    todo = app.add("  task with spaces  ")

    assert todo.text == "task with spaces"


def test_whitespace_handling_consistency() -> None:
    """All three entry points should handle whitespace consistently."""
    # All three should produce the same result
    text_with_spaces = "  same text  "

    # Direct Todo construction
    todo1 = Todo(id=1, text=text_with_spaces)

    # TodoApp.add()
    app = TodoApp(db_path=":memory:")
    todo2 = app.add(text_with_spaces)

    # Todo.rename()
    todo3 = Todo(id=3, text="original")
    todo3.rename(text_with_spaces)

    # All should have stripped whitespace
    expected = "same text"
    assert todo1.text == expected, f"Todo.__init__ should strip: got {todo1.text!r}"
    assert todo2.text == expected, f"TodoApp.add() should strip: got {todo2.text!r}"
    assert todo3.text == expected, f"Todo.rename() should strip: got {todo3.text!r}"


def test_todo_init_empty_after_strip_raises() -> None:
    """Todo.__init__ should raise ValueError if text is empty after stripping."""
    import pytest

    with pytest.raises(ValueError, match="cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_init_preserves_internal_whitespace() -> None:
    """Todo.__init__ should preserve internal whitespace."""
    todo = Todo(id=1, text="  hello   world  ")

    # Should strip leading/trailing but preserve internal whitespace
    assert todo.text == "hello   world"
