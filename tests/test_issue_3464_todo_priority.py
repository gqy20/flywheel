"""Tests for Todo priority field (Issue #3464).

These tests verify that:
1. Todo can specify priority=1/2/3 (high/medium/low)
2. from_dict parses priority field (defaults to 2 if missing)
3. to_dict includes priority
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_can_specify_high_priority() -> None:
    """Todo should accept priority=1 (high)."""
    todo = Todo(id=1, text="urgent task", priority=1)
    assert todo.priority == 1


def test_todo_can_specify_medium_priority() -> None:
    """Todo should accept priority=2 (medium)."""
    todo = Todo(id=1, text="normal task", priority=2)
    assert todo.priority == 2


def test_todo_can_specify_low_priority() -> None:
    """Todo should accept priority=3 (low)."""
    todo = Todo(id=1, text="later task", priority=3)
    assert todo.priority == 3


def test_todo_default_priority_is_medium() -> None:
    """Todo without priority should default to 2 (medium)."""
    todo = Todo(id=1, text="default priority task")
    assert todo.priority == 2


def test_from_dict_parses_priority() -> None:
    """from_dict should parse the priority field."""
    todo = Todo.from_dict({"id": 1, "text": "high priority", "priority": 1})
    assert todo.priority == 1


def test_from_dict_defaults_priority_to_2() -> None:
    """from_dict should default priority to 2 when missing."""
    todo = Todo.from_dict({"id": 1, "text": "no priority specified"})
    assert todo.priority == 2


def test_to_dict_includes_priority() -> None:
    """to_dict should include the priority field."""
    todo = Todo(id=1, text="test", priority=1)
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 1


def test_to_dict_includes_default_priority() -> None:
    """to_dict should include priority even when using default."""
    todo = Todo(id=1, text="test")  # Uses default priority
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 2
