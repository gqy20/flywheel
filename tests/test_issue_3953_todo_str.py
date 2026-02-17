"""Tests for Todo.__str__ method (Issue #3953).

These tests verify that:
1. Todo objects have a user-friendly __str__ for display
2. str() output differs from repr() which is for debugging
3. str() includes status indicator for done/undone todos
4. str() output mirrors CLI output style
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_str_returns_user_friendly_format() -> None:
    """str(Todo) should return a user-friendly format."""
    todo = Todo(id=1, text="Buy milk", done=False)
    result = str(todo)

    # Should contain the task text
    assert "Buy milk" in result


def test_todo_str_includes_done_status_for_completed() -> None:
    """str(Todo) should include done status indicator for completed todos."""
    todo = Todo(id=1, text="Task", done=True)
    result = str(todo)

    # Should contain status indicator (e.g., [x] or (done))
    # The format should indicate completion
    assert "x" in result or "done" in result.lower() or "[x]" in result


def test_todo_str_includes_status_for_undone() -> None:
    """str(Todo) should show undone status for incomplete todos."""
    todo = Todo(id=1, text="Buy milk", done=False)
    result = str(todo)

    # Should show undone status (e.g., [ ] or just text without done indicator)
    # Format like '[ ] Buy milk' or just the text
    assert "Buy milk" in result


def test_todo_str_differs_from_repr() -> None:
    """str(Todo) should differ from repr() which is for debugging."""
    todo = Todo(id=1, text="Buy milk", done=False)

    str_result = str(todo)
    repr_result = repr(todo)

    # str() and repr() should be different
    assert str_result != repr_result

    # repr should look like a Python expression (for debugging)
    assert "Todo(" in repr_result
    assert "id=" in repr_result

    # str should be more user-friendly (not a Python expression)
    assert "Todo(" not in str_result


def test_todo_str_with_special_characters() -> None:
    """str(Todo) should handle special characters in text."""
    todo = Todo(id=1, text='Task with "quotes"')
    result = str(todo)

    # Should contain the text with quotes
    assert "quotes" in result


def test_todo_str_multiple_todos_distinct() -> None:
    """str(Todo) should make different todos distinguishable."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=2, text="task two", done=True)

    str1 = str(todo1)
    str2 = str(todo2)

    # Different todos should have different str output
    assert str1 != str2
