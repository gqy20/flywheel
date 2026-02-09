"""Regression tests for Issue #2567: format_list None input validation.

This test file ensures that format_list properly validates its input:
- format_list(None) should raise TypeError instead of silently returning "No todos yet."
- format_list([None]) should raise TypeError with clear message about None items
- format_list([]) should still return "No todos yet." (existing behavior preserved)
"""

from __future__ import annotations

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_list_none_input_raises_typeerror() -> None:
    """format_list(None) should raise TypeError instead of returning 'No todos yet.'"""
    with pytest.raises(TypeError, match="todos must be a list"):
        TodoFormatter.format_list(None)  # type: ignore[arg-type]


def test_format_list_list_containing_none_raises_typeerror() -> None:
    """format_list([None]) should raise TypeError with clear message about None items."""
    with pytest.raises(TypeError, match="todo items must be Todo instances"):
        TodoFormatter.format_list([None])  # type: ignore[list-item]


def test_format_list_list_containing_mixed_none_and_todo_raises_typeerror() -> None:
    """format_list with mixed None and Todo items should raise TypeError."""
    todos = [Todo(id=1, text="Valid task"), None]  # type: ignore[list-item]
    with pytest.raises(TypeError, match="todo items must be Todo instances"):
        TodoFormatter.format_list(todos)


def test_format_list_empty_list_still_works() -> None:
    """format_list([]) should still return 'No todos yet.' (existing behavior preserved)."""
    result = TodoFormatter.format_list([])
    assert result == "No todos yet."


def test_format_list_with_valid_todos_still_works() -> None:
    """format_list with valid Todo items should work as before."""
    todos = [
        Todo(id=1, text="Task 1"),
        Todo(id=2, text="Task 2"),
    ]
    result = TodoFormatter.format_list(todos)
    assert "[ ]   1 Task 1" in result
    assert "[ ]   2 Task 2" in result
