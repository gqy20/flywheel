"""Tests for Todo.__str__ method (Issue #5973).

These tests verify that:
1. Todo objects have a user-friendly __str__ for printing
2. str output follows the format: '[x] #<id> <text>' (done) or '[ ] #<id> <text>' (not done)
3. __str__ complements the debug-focused __repr__
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_str_format_not_done() -> None:
    """str(Todo) should return user-friendly format for incomplete todo."""
    todo = Todo(id=1, text="Buy milk", done=False)
    result = str(todo)

    # Should match format: '[ ] #1 Buy milk'
    assert result == "[ ] #1 Buy milk"


def test_todo_str_format_done() -> None:
    """str(Todo) should return user-friendly format for completed todo."""
    todo = Todo(id=1, text="Buy milk", done=True)
    result = str(todo)

    # Should match format: '[x] #1 Buy milk'
    assert result == "[x] #1 Buy milk"


def test_todo_str_shows_x_when_done() -> None:
    """str(Todo) should show 'x' in status bracket when done=True."""
    todo = Todo(id=1, text="x", done=True)
    result = str(todo)

    # Should contain 'x' in the status bracket
    assert "[x]" in result


def test_todo_str_shows_space_when_not_done() -> None:
    """str(Todo) should show space in status bracket when done=False."""
    todo = Todo(id=1, text="task", done=False)
    result = str(todo)

    # Should contain space in the status bracket
    assert "[ ]" in result


def test_todo_str_includes_id() -> None:
    """str(Todo) should include the todo id."""
    todo = Todo(id=42, text="some task", done=False)
    result = str(todo)

    # Should include id with hash prefix
    assert "#42" in result


def test_todo_str_includes_text() -> None:
    """str(Todo) should include the todo text."""
    todo = Todo(id=1, text="Complete the feature", done=False)
    result = str(todo)

    # Should include the text
    assert "Complete the feature" in result


def test_todo_str_different_from_repr() -> None:
    """str(Todo) should be different from repr(Todo)."""
    todo = Todo(id=1, text="Buy milk", done=False)

    str_result = str(todo)
    repr_result = repr(todo)

    # str should be user-friendly, repr should be debug-focused
    assert str_result != repr_result
    # repr should contain class name, str should not
    assert "Todo(" in repr_result
    assert "Todo(" not in str_result


def test_todo_str_multiple_todos_distinct() -> None:
    """str(Todo) should make different todos distinguishable."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=2, text="task two", done=True)

    str1 = str(todo1)
    str2 = str(todo2)

    # Different todos should have different str outputs
    assert str1 != str2
    assert "#1" in str1
    assert "#2" in str2
