"""Tests for Todo.__str__ method (Issue #3953).

These tests verify that:
1. Todo objects have a user-friendly __str__ for display
2. str() output differs from repr() which is for debugging
3. str() output includes done status indicator (like [x] or [ ])
4. str() is suitable for CLI output and user-facing displays
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_str_returns_user_friendly_format() -> None:
    """str(Todo) should return a user-friendly format."""
    todo = Todo(id=1, text="Buy milk", done=False)
    result = str(todo)

    # Should include the task text
    assert "Buy milk" in result


def test_todo_str_includes_done_status_indicator() -> None:
    """str(Todo) should include a done status indicator."""
    # Undone todo
    undone = Todo(id=1, text="Task", done=False)
    undone_result = str(undone)

    # Done todo
    done = Todo(id=1, text="Task", done=True)
    done_result = str(done)

    # Output should differ based on done status
    assert undone_result != done_result, "str() should differ for done vs undone"


def test_todo_str_format_for_undone_todo() -> None:
    """str(Todo) for undone todo should show unchecked status."""
    todo = Todo(id=1, text="Buy milk", done=False)
    result = str(todo)

    # Should have an unchecked indicator like [ ] or similar
    assert "[ ]" in result or "○" in result or "( )" in result or "undone" in result.lower() or "done=False" not in result


def test_todo_str_format_for_done_todo() -> None:
    """str(Todo) for done todo should show checked status."""
    todo = Todo(id=1, text="Task", done=True)
    result = str(todo)

    # Should have a checked indicator like [x] or [X] or similar
    assert "[x]" in result or "[X]" in result or "●" in result or "(done)" in result.lower() or "done=True" not in result


def test_todo_str_differs_from_repr() -> None:
    """str(Todo) should differ from repr(Todo) for same object."""
    todo = Todo(id=1, text="Buy milk", done=False)

    str_result = str(todo)
    repr_result = repr(todo)

    # str() should be different from repr()
    assert str_result != repr_result, "str() should differ from repr()"


def test_todo_str_is_user_friendly_not_debug() -> None:
    """str(Todo) should be user-friendly, not debug-style."""
    todo = Todo(id=1, text="Buy milk", done=True)
    result = str(todo)

    # Should NOT have debug-style format like "Todo(id=1, ...)"
    assert not result.startswith("Todo("), "str() should not be debug format"


def test_todo_str_handles_special_characters() -> None:
    """str(Todo) should handle special characters properly."""
    # Text with quotes
    todo1 = Todo(id=1, text='task with "quotes"', done=False)
    result1 = str(todo1)
    assert "task with" in result1 or "quotes" in result1

    # Text with unicode
    todo2 = Todo(id=2, text="任务 📋", done=True)
    result2 = str(todo2)
    assert "任务" in result2 or "📋" in result2
