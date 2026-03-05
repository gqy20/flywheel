"""Tests for Todo constructor text validation (Issue #7287).

These tests verify that the Todo constructor strips and validates text
just like the rename() method does.

Acceptance criteria:
- Todo(id=1, text='  ') should raise ValueError
- Todo(id=1, text='  task  ') should store 'task' (stripped)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_whitespace_only_text() -> None:
    """Issue #7287: Todo constructor should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  ")


def test_todo_constructor_rejects_whitespace_only_variants() -> None:
    """Issue #7287: Todo constructor should reject various whitespace-only strings."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\n")


def test_todo_constructor_strips_whitespace() -> None:
    """Issue #7287: Todo constructor should strip leading/trailing whitespace."""
    todo = Todo(id=1, text="  task  ")
    assert todo.text == "task"


def test_todo_constructor_preserves_valid_text() -> None:
    """Issue #7287: Todo constructor should preserve valid text without padding."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"
