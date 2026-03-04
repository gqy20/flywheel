"""Tests for Todo.__init__ text validation (Issue #7107).

These tests verify that Todo.__init__ strips and validates the 'text' parameter
at construction time, consistent with rename() and cli.add() behavior.

Acceptance criteria:
- Todo(id=1, text=' valid ') stores text as 'valid' (stripped)
- Todo(id=1, text='') raises ValueError
- Todo(id=1, text=' ') raises ValueError
- Todo(id=1, text='\\t\\n') raises ValueError
- Behavior consistent with rename() method
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_strips_whitespace_from_text() -> None:
    """Todo.__init__ should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text=" valid ")
    assert todo.text == "valid", f"Expected stripped text 'valid', got {todo.text!r}"


def test_todo_init_strips_leading_whitespace() -> None:
    """Todo.__init__ should strip leading whitespace."""
    todo = Todo(id=1, text="\tleading")
    assert todo.text == "leading", f"Expected 'leading', got {todo.text!r}"


def test_todo_init_strips_trailing_whitespace() -> None:
    """Todo.__init__ should strip trailing whitespace."""
    todo = Todo(id=1, text="trailing\n")
    assert todo.text == "trailing", f"Expected 'trailing', got {todo.text!r}"


def test_todo_init_raises_on_empty_text() -> None:
    """Todo.__init__ should raise ValueError for empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_raises_on_whitespace_only_text() -> None:
    """Todo.__init__ should raise ValueError for whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_todo_init_raises_on_tabs_and_newlines_only() -> None:
    """Todo.__init__ should raise ValueError for tabs/newlines only."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_init_consistent_with_rename() -> None:
    """Todo.__init__ validation should be consistent with rename()."""
    # rename() strips text
    todo = Todo(id=1, text="original")
    todo.rename(" renamed ")
    assert todo.text == "renamed"

    # __init__ should also strip text
    todo2 = Todo(id=2, text=" init ")
    assert todo2.text == "init"


def test_todo_from_dict_strips_text() -> None:
    """Todo.from_dict should also strip text for consistency."""
    todo = Todo.from_dict({"id": 1, "text": " from dict "})
    assert todo.text == "from dict", f"Expected 'from dict', got {todo.text!r}"


def test_todo_from_dict_raises_on_empty_text() -> None:
    """Todo.from_dict should raise ValueError for empty text after stripping."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})
