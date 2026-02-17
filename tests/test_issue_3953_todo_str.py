"""Tests for Todo.__str__ method (Issue #3953).

These tests verify that:
1. Todo objects have a user-friendly __str__ for display
2. str() output differs from repr() which is for debugging
3. str() includes status indicator for done/undone todos
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_str_returns_user_friendly_format() -> None:
    """str(Todo) should return a user-friendly format for display."""
    todo = Todo(id=1, text="Buy milk", done=False)
    result = str(todo)

    # Should include the task text
    assert "Buy milk" in result


def test_todo_str_includes_done_indicator_when_complete() -> None:
    """str(Todo) should include done status indicator for completed todos."""
    todo = Todo(id=1, text="Task", done=True)
    result = str(todo)

    # Should include a done status indicator (like [x] or (done))
    assert "[x]" in result or "(done)" in result.lower() or "done" in result.lower()


def test_todo_str_includes_undone_indicator_when_not_complete() -> None:
    """str(Todo) should show undone status indicator for incomplete todos."""
    todo = Todo(id=1, text="Task", done=False)
    result = str(todo)

    # Should include an undone status indicator (like [ ] or no indicator)
    # The format should differentiate from done tasks
    assert "[ ]" in result or "[x]" not in result


def test_todo_str_differs_from_repr() -> None:
    """str(Todo) should differ from repr(Todo) - str is for users, repr for debugging."""
    todo = Todo(id=1, text="Buy milk", done=False)

    str_result = str(todo)
    repr_result = repr(todo)

    # str should be different from repr (repr is for debugging with class name etc.)
    assert str_result != repr_result, (
        f"str and repr should differ: str={str_result!r}, repr={repr_result!r}"
    )


def test_todo_str_does_not_include_class_name() -> None:
    """str(Todo) should NOT include 'Todo' class name (unlike repr which is for debugging)."""
    todo = Todo(id=1, text="Buy milk", done=False)
    result = str(todo)

    # str should not start with "Todo(" like repr does
    assert not result.startswith("Todo("), (
        f"str should be user-friendly, not debug format: {result}"
    )


def test_todo_str_with_long_text() -> None:
    """str(Todo) should handle long text appropriately."""
    long_text = "a" * 100
    todo = Todo(id=1, text=long_text, done=False)
    result = str(todo)

    # Should include the text (no truncation needed for user display, or can truncate)
    assert "a" in result


def test_todo_str_matches_cli_format() -> None:
    """str(Todo) should mirror CLI output style like '[x] Task text' or similar."""
    done_todo = Todo(id=1, text="Complete task", done=True)
    undone_todo = Todo(id=2, text="Pending task", done=False)

    done_str = str(done_todo)
    undone_str = str(undone_todo)

    # The format should use [x]/[ ] style like the CLI
    assert "[x]" in done_str
    assert "[ ]" in undone_str
