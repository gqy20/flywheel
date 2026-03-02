"""Tests for Todo.__str__ method (Issue #6720).

These tests verify that:
1. Todo objects have a user-friendly __str__ for display
2. str(Todo) returns format like '[x] #1: todo text'
3. str output is concise (< 80 chars for normal todos)
4. __str__ differs from __repr__ (which is debug-oriented)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_str_with_undone_todo() -> None:
    """str(Todo) should return user-friendly format for undone todo."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = str(todo)

    # Should match format: '[ ] #1: buy milk'
    assert result == "[ ] #1: buy milk"


def test_todo_str_with_done_todo() -> None:
    """str(Todo) should return user-friendly format for done todo."""
    todo = Todo(id=1, text="buy milk", done=True)
    result = str(todo)

    # Should match format: '[x] #1: buy milk'
    assert result == "[x] #1: buy milk"


def test_todo_str_is_concise() -> None:
    """str(Todo) output should be concise (< 80 chars for normal todos)."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = str(todo)

    assert len(result) < 80, f"str too long: {len(result)} chars - {result}"


def test_todo_str_differs_from_repr() -> None:
    """str(Todo) should differ from repr(Todo) - user vs debug format."""
    todo = Todo(id=1, text="buy milk", done=False)

    str_result = str(todo)
    repr_result = repr(todo)

    # str should be user-friendly, repr should be debug-friendly
    assert str_result != repr_result
    # repr contains class name and field names
    assert "Todo(" in repr_result
    assert "id=" in repr_result
    # str is simpler, just the display format
    assert "Todo(" not in str_result


def test_todo_str_with_different_ids() -> None:
    """str(Todo) should correctly display different todo IDs."""
    todo42 = Todo(id=42, text="task forty-two", done=False)
    result = str(todo42)

    assert "#42" in result
    assert "task forty-two" in result


def test_todo_str_handles_special_characters() -> None:
    """str(Todo) should handle special characters in text."""
    # Text with quotes
    todo1 = Todo(id=1, text='task with "quotes"', done=False)
    result1 = str(todo1)
    assert 'task with "quotes"' in result1

    # Text with emoji (should work in modern Python)
    todo2 = Todo(id=2, text="buy groceries", done=True)
    result2 = str(todo2)
    assert "[x]" in result2
    assert "buy groceries" in result2
