"""Tests for Todo priority field support (Issue #3464).

These tests verify that:
1. Todo can be created with priority=1/2/3
2. Todo.from_dict parses priority field (defaults to 2 if missing)
3. Todo.to_dict includes priority field
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_can_be_created_with_priority() -> None:
    """Todo should accept priority=1 (high priority)."""
    todo = Todo(id=1, text="urgent task", priority=1)
    assert todo.priority == 1


def test_todo_default_priority_is_medium() -> None:
    """Todo should default to priority=2 (medium) when not specified."""
    todo = Todo(id=1, text="normal task")
    assert todo.priority == 2


def test_todo_from_dict_parses_priority() -> None:
    """Todo.from_dict should parse priority field from dict."""
    todo = Todo.from_dict({"id": 1, "text": "task", "priority": 1})
    assert todo.priority == 1


def test_todo_from_dict_defaults_priority_to_two() -> None:
    """Todo.from_dict should default priority to 2 when missing."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.priority == 2


def test_todo_to_dict_includes_priority() -> None:
    """Todo.to_dict should include priority field."""
    todo = Todo(id=1, text="task", priority=3)
    d = todo.to_dict()
    assert "priority" in d
    assert d["priority"] == 3


def test_todo_from_dict_with_all_priorities() -> None:
    """Todo.from_dict should accept all valid priority values (1, 2, 3)."""
    for prio in [1, 2, 3]:
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": prio})
        assert todo.priority == prio
