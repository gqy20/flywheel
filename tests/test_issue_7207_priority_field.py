"""Tests for Todo priority field (Issue #7207).

These tests verify that:
1. Todo supports an optional priority field, defaulting to 0
2. from_dict() correctly loads old data without priority field
3. to_dict() output includes priority field
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_supports_priority_field() -> None:
    """Todo should support an optional priority field."""
    todo = Todo(id=1, text="high priority task", priority=3)
    assert todo.priority == 3


def test_todo_priority_defaults_to_zero() -> None:
    """Todo priority should default to 0 when not specified."""
    todo = Todo(id=1, text="default priority task")
    assert todo.priority == 0


def test_from_dict_loads_old_data_without_priority() -> None:
    """from_dict() should correctly load old data without priority field."""
    data = {"id": 1, "text": "legacy task"}
    todo = Todo.from_dict(data)
    assert todo.priority == 0


def test_from_dict_loads_priority_when_present() -> None:
    """from_dict() should load priority when present in data."""
    data = {"id": 1, "text": "task with priority", "priority": 2}
    todo = Todo.from_dict(data)
    assert todo.priority == 2


def test_to_dict_includes_priority() -> None:
    """to_dict() output should include priority field."""
    todo = Todo(id=1, text="task", priority=1)
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 1


def test_to_dict_includes_priority_default() -> None:
    """to_dict() output should include priority field even when default."""
    todo = Todo(id=1, text="task")
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 0


def test_priority_roundtrip() -> None:
    """Priority should survive roundtrip through to_dict/from_dict."""
    original = Todo(id=1, text="task", priority=2)
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.priority == original.priority
