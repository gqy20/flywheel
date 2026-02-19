"""Regression tests for issue #4425: Todo text validation on construction.

Bug: Todo text is not stripped/validated on construction, only in rename() method,
allowing whitespace-only todos.

Fix: Add text validation in __post_init__ to strip and validate text is not empty
after stripping, consistent with rename() method.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_construction_rejects_whitespace_only_text() -> None:
    """Bug #4425: Todo construction should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  ")


def test_todo_construction_rejects_whitespace_only_variants() -> None:
    """Bug #4425: Todo construction should reject various whitespace patterns."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" \t \n ")


def test_todo_construction_strips_and_stores_padded_text() -> None:
    """Bug #4425: Todo construction should strip whitespace from valid text."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #4425: Todo.from_dict() should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "  "})


def test_todo_from_dict_strips_and_stores_padded_text() -> None:
    """Bug #4425: Todo.from_dict() should strip whitespace from valid text."""
    todo = Todo.from_dict({"id": 1, "text": "  padded  "})
    assert todo.text == "padded"


def test_todo_construction_rejects_empty_string() -> None:
    """Bug #4425: Todo construction should reject empty text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")
