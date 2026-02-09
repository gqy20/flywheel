"""Regression tests for Issue #2567: format_list None input handling.

This test file ensures that format_list properly handles None input and lists
containing None items with appropriate error messages instead of silent failure
or unclear crashes.
"""

from __future__ import annotations

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_list_none_raises_typeerror() -> None:
    """format_list(None) should raise TypeError instead of returning 'No todos yet.'

    The current implementation uses 'if not todos' which treats None as falsy,
    silently returning 'No todos yet.' instead of raising an error about
    incorrect input type.
    """
    with pytest.raises(TypeError, match="todos must be a list"):
        TodoFormatter.format_list(None)  # type: ignore[arg-type]


def test_format_list_list_with_none_raises_valueerror() -> None:
    """format_list([None]) should raise a clear error about None items in list.

    When a list contains None items, the current implementation crashes with
    AttributeError: 'NoneType' object has no attribute 'done' which is
    unclear. This should raise a more descriptive error.
    """
    with pytest.raises(ValueError, match="contains None item"):
        TodoFormatter.format_list([None])  # type: ignore[list-item]


def test_format_list_empty_still_works() -> None:
    """Empty list should still return 'No todos yet.' (regression check).

    This ensures the fix doesn't break the existing valid behavior.
    """
    result = TodoFormatter.format_list([])
    assert result == "No todos yet."


def test_format_list_valid_todos_still_works() -> None:
    """Valid todo list should still work correctly (regression check)."""
    todos = [
        Todo(id=1, text="Task 1"),
        Todo(id=2, text="Task 2"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    assert len(lines) == 2
    assert "[ ]   1 Task 1" in lines[0]
    assert "[ ]   2 Task 2" in lines[1]


def test_format_list_list_with_mixed_none_and_valid() -> None:
    """List with mix of None and valid todos should raise error about None items."""
    todos = [
        Todo(id=1, text="Task 1"),
        None,  # type: ignore[list-item]
        Todo(id=2, text="Task 2"),
    ]
    with pytest.raises(ValueError, match="contains None item"):
        TodoFormatter.format_list(todos)
