"""Regression tests for Issue #2567: format_list None input handling.

This test file ensures that:
1. format_list(None) raises TypeError instead of returning 'No todos yet.'
2. format_list([None]) raises a clear error about None items in list
3. format_list([]) still returns 'No todos yet.'
"""

from __future__ import annotations

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_list_none_raises_typeerror() -> None:
    """format_list(None) should raise TypeError instead of returning 'No todos yet.'"""
    with pytest.raises(TypeError, match="todos must be a list"):
        TodoFormatter.format_list(None)  # type: ignore[arg-type]


def test_format_list_list_with_none_raises_valueerror() -> None:
    """format_list([None]) should raise ValueError about None items in list."""
    with pytest.raises(ValueError, match="todo list contains None items"):
        TodoFormatter.format_list([None])  # type: ignore[list-item]


def test_format_list_list_with_mixed_none_and_valid_raises_valueerror() -> None:
    """format_list with list containing both None and valid todos should raise ValueError."""
    todos = [Todo(id=1, text="Valid task"), None, Todo(id=2, text="Another task")]  # type: ignore[list-item]
    with pytest.raises(ValueError, match="todo list contains None items"):
        TodoFormatter.format_list(todos)


def test_format_list_empty_returns_message() -> None:
    """format_list([]) should still return 'No todos yet.'"""
    result = TodoFormatter.format_list([])
    assert result == "No todos yet."


def test_format_list_valid_todos_works() -> None:
    """format_list with valid Todo objects should work correctly."""
    todos = [
        Todo(id=1, text="Buy milk"),
        Todo(id=2, text="Write code"),
    ]
    result = TodoFormatter.format_list(todos)
    assert result == "[ ]   1 Buy milk\n[ ]   2 Write code"
