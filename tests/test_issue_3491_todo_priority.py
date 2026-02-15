"""Tests for Todo priority field support (Issue #3491).

These tests verify that:
1. Todo dataclass includes priority: int = 0 field
2. from_dict() can parse priority field (defaults to 0)
3. to_dict() output includes priority
4. Priority field serialization and deserialization works correctly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_priority_field() -> None:
    """Todo should have a priority field with default value 0."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "priority")
    assert todo.priority == 0


def test_todo_priority_can_be_set() -> None:
    """Todo priority can be explicitly set to a custom value."""
    todo = Todo(id=1, text="urgent task", priority=2)
    assert todo.priority == 2


def test_todo_from_dict_with_priority() -> None:
    """Todo.from_dict() should parse priority field from dict."""
    data = {"id": 1, "text": "high priority task", "priority": 5}
    todo = Todo.from_dict(data)
    assert todo.priority == 5


def test_todo_from_dict_priority_defaults_to_zero() -> None:
    """Todo.from_dict() should default priority to 0 when not provided."""
    data = {"id": 1, "text": "task without priority"}
    todo = Todo.from_dict(data)
    assert todo.priority == 0


def test_todo_to_dict_includes_priority() -> None:
    """Todo.to_dict() output should include priority field."""
    todo = Todo(id=1, text="task", priority=3)
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 3


def test_todo_to_dict_priority_default_included() -> None:
    """Todo.to_dict() should include priority even when using default value."""
    todo = Todo(id=1, text="task")  # priority defaults to 0
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 0


def test_todo_priority_roundtrip() -> None:
    """Priority should survive serialization/deserialization roundtrip."""
    original = Todo(id=1, text="important", priority=10)
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.priority == original.priority


def test_todo_priority_negative_value() -> None:
    """Todo priority can be negative (lower number = higher priority)."""
    # Unix convention: lower values = higher priority
    todo = Todo(id=1, text="critical task", priority=-1)
    assert todo.priority == -1


def test_todo_from_dict_with_negative_priority() -> None:
    """Todo.from_dict() should handle negative priority values."""
    data = {"id": 1, "text": "urgent", "priority": -5}
    todo = Todo.from_dict(data)
    assert todo.priority == -5
