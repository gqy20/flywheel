"""Tests for Todo constructor text validation edge cases (Issue #7289).

These tests verify that:
1. Todo constructor rejects empty string text
2. Todo constructor rejects whitespace-only text
3. Todo constructor strips leading/trailing whitespace from text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Todo constructor should reject empty string for text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Todo constructor should reject whitespace-only text."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    # Also test tabs and mixed whitespace
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t\t")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="  \t  \n  ")


def test_todo_constructor_strips_whitespace() -> None:
    """Todo constructor should strip leading/trailing whitespace from text."""
    todo = Todo(id=1, text="  valid  ")
    assert todo.text == "valid"

    # Test with leading whitespace only
    todo2 = Todo(id=2, text="  leading")
    assert todo2.text == "leading"

    # Test with trailing whitespace only
    todo3 = Todo(id=3, text="trailing  ")
    assert todo3.text == "trailing"
