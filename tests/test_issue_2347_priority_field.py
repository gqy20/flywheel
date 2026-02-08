"""Tests for priority field support (Issue #2347)."""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_todo_has_default_priority_zero() -> None:
    """Issue #2347: Todo class should have priority field with default value 0."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "priority"), "Todo should have priority attribute"
    assert todo.priority == 0, "Default priority should be 0 (no priority)"


def test_todo_accepts_explicit_priority() -> None:
    """Issue #2347: Todo should accept explicit priority values."""
    todo = Todo(id=1, text="high priority task", priority=3)
    assert todo.priority == 3


def test_todo_from_dict_parses_priority() -> None:
    """Issue #2347: Todo.from_dict should correctly parse priority field."""
    data = {
        "id": 1,
        "text": "medium priority task",
        "done": False,
        "priority": 2,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }
    todo = Todo.from_dict(data)
    assert todo.priority == 2


def test_todo_from_dict_defaults_priority_to_zero() -> None:
    """Issue #2347: Todo.from_dict should default priority to 0 when not provided."""
    data = {
        "id": 1,
        "text": "task without priority",
        "done": False,
    }
    todo = Todo.from_dict(data)
    assert todo.priority == 0


def test_todo_to_dict_includes_priority() -> None:
    """Issue #2347: Todo.to_dict should include priority field."""
    todo = Todo(id=1, text="task", priority=2)
    todo_dict = todo.to_dict()
    assert "priority" in todo_dict
    assert todo_dict["priority"] == 2


def test_formatter_shows_no_marker_for_priority_zero() -> None:
    """Issue #2347: TodoFormatter should not show priority marker for priority=0."""
    todo = Todo(id=1, text="normal task", priority=0, done=False)
    formatted = TodoFormatter.format_todo(todo)
    assert "[P1]" not in formatted
    assert "[P2]" not in formatted
    assert "[P3]" not in formatted


def test_formatter_shows_p1_marker_for_priority_one() -> None:
    """Issue #2347: TodoFormatter should show [P1] marker for priority=1."""
    todo = Todo(id=1, text="low priority task", priority=1, done=False)
    formatted = TodoFormatter.format_todo(todo)
    assert "[P1]" in formatted


def test_formatter_shows_p2_marker_for_priority_two() -> None:
    """Issue #2347: TodoFormatter should show [P2] marker for priority=2."""
    todo = Todo(id=1, text="medium priority task", priority=2, done=False)
    formatted = TodoFormatter.format_todo(todo)
    assert "[P2]" in formatted


def test_formatter_shows_p3_marker_for_priority_three() -> None:
    """Issue #2347: TodoFormatter should show [P3] marker for priority=3."""
    todo = Todo(id=1, text="high priority task", priority=3, done=False)
    formatted = TodoFormatter.format_todo(todo)
    assert "[P3]" in formatted


def test_formatter_shows_done_status_with_priority() -> None:
    """Issue #2347: TodoFormatter should show both done status and priority marker."""
    todo = Todo(id=1, text="done high priority task", priority=3, done=True)
    formatted = TodoFormatter.format_todo(todo)
    assert "[x]" in formatted
    assert "[P3]" in formatted
