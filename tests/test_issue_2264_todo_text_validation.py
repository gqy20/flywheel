"""Regression tests for issue #2264: Todo.__init__/__post_init__ text validation.

Bug: Todo.__init__/__post_init__ does not validate that text is non-empty,
creating inconsistency with the rename method which properly validates text.

This test file ensures:
1. Direct Todo construction validates text is non-empty after stripping
2. Todo.from_dict validates text is non-empty after stripping
3. Behavior matches the rename method
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_string() -> None:
    """Bug #2264: Todo.__init__ should reject empty strings after strip."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_init_rejects_whitespace_only() -> None:
    """Bug #2264: Todo.__init__ should reject whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text=" ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_from_dict_rejects_empty_text() -> None:
    """Bug #2264: Todo.from_dict should reject empty text after strip."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #2264: Todo.from_dict should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": " "})

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n"})


def test_todo_init_strips_whitespace() -> None:
    """Bug #2264: Todo.__init__ should strip whitespace like rename does."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"


def test_todo_from_dict_strips_whitespace() -> None:
    """Bug #2264: Todo.from_dict should strip whitespace like rename does."""
    todo = Todo.from_dict({"id": 1, "text": "  padded  "})
    assert todo.text == "padded"


def test_todo_rename_behavior_unchanged() -> None:
    """Bug #2264: Ensure rename method behavior remains unchanged."""
    todo = Todo(id=1, text="original")

    # Valid rename should work
    todo.rename("new text")
    assert todo.text == "new text"

    # Whitespace should be stripped
    todo.rename("  padded  ")
    assert todo.text == "padded"

    # Empty should raise ValueError
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.rename("")
