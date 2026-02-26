"""Tests for Todo.__str__ method (Issue #5973).

These tests verify that:
1. str(Todo) returns a user-friendly string representation
2. Format matches: [x] #<id> <text> for done, [ ] #<id> <text> for not done
3. __str__ complements the debug-focused __repr__
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_str_undone_format() -> None:
    """str(Todo) should return user-friendly format for undone todo."""
    todo = Todo(id=1, text="Buy milk", done=False)
    result = str(todo)

    assert result == "[ ] #1 Buy milk"


def test_todo_str_done_format() -> None:
    """str(Todo) should return user-friendly format for done todo."""
    todo = Todo(id=1, text="Buy milk", done=True)
    result = str(todo)

    assert result == "[x] #1 Buy milk"


def test_todo_str_with_different_id() -> None:
    """str(Todo) should correctly display different ids."""
    todo = Todo(id=42, text="Test task", done=False)
    result = str(todo)

    assert result == "[ ] #42 Test task"


def test_todo_str_mark_done_changes_output() -> None:
    """str(Todo) should reflect done state changes."""
    todo = Todo(id=1, text="x", done=False)
    assert "[ ]" in str(todo)

    todo.mark_done()
    assert "[x]" in str(todo)


def test_todo_str_distinct_from_repr() -> None:
    """str(Todo) should be more user-friendly than repr(Todo)."""
    todo = Todo(id=1, text="Buy milk", done=False)
    str_result = str(todo)
    repr_result = repr(todo)

    # str should be more concise and user-friendly
    # repr shows "Todo(id=1, text='Buy milk', done=False)"
    # str shows "[ ] #1 Buy milk"
    assert str_result != repr_result
    assert str_result == "[ ] #1 Buy milk"
    assert "Todo(" not in str_result


def test_todo_str_with_long_text() -> None:
    """str(Todo) should not truncate long text (unlike repr)."""
    long_text = "a" * 100
    todo = Todo(id=1, text=long_text, done=False)
    result = str(todo)

    # Unlike repr which truncates, str should show full text
    assert long_text in result
    assert "..." not in result
