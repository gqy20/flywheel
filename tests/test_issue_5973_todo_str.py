"""Tests for Todo.__str__ method (Issue #5973).

These tests verify that:
1. Todo objects have a user-friendly __str__ method
2. str output matches the format: '[ ] #<id> <text>' for undone
3. str output matches the format: '[x] #<id> <text>' for done
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_str_undone_format() -> None:
    """str(Todo) should return user-friendly format for undone todos."""
    todo = Todo(id=1, text="Buy milk", done=False)
    result = str(todo)

    assert result == "[ ] #1 Buy milk"


def test_todo_str_done_format() -> None:
    """str(Todo) should return user-friendly format for done todos."""
    todo = Todo(id=1, text="Buy milk", done=True)
    result = str(todo)

    assert result == "[x] #1 Buy milk"


def test_todo_str_with_different_id() -> None:
    """str(Todo) should include correct id in output."""
    todo = Todo(id=42, text="Task", done=False)
    result = str(todo)

    assert result == "[ ] #42 Task"


def test_todo_str_distinct_from_repr() -> None:
    """str(Todo) should be different from repr (user-friendly vs debug)."""
    todo = Todo(id=1, text="Buy milk", done=False)

    str_result = str(todo)
    repr_result = repr(todo)

    # str should be user-friendly format
    assert str_result == "[ ] #1 Buy milk"
    # repr should be debug format
    assert "Todo(" in repr_result
    # They should be different
    assert str_result != repr_result


def test_todo_str_done_state_changes_output() -> None:
    """str(Todo) should show 'x' for done and ' ' for undone."""
    todo_undone = Todo(id=1, text="Task", done=False)
    todo_done = Todo(id=1, text="Task", done=True)

    assert "x" not in str(todo_undone)
    assert "x" in str(todo_done)
