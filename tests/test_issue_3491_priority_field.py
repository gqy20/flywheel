"""Tests for Todo priority field (Issue #3491).

These tests verify that:
1. Todo dataclass contains priority: int = 0 field
2. from_dict() can parse priority field (default 0)
3. to_dict() output includes priority
4. Priority field serialization and deserialization works correctly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_priority_field_with_default_zero() -> None:
    """Todo should have a priority field with default value 0."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "priority")
    assert todo.priority == 0


def test_todo_priority_can_be_set() -> None:
    """Todo priority can be set to a specific value."""
    todo = Todo(id=1, text="high priority task", priority=2)
    assert todo.priority == 2


def test_todo_from_dict_parses_priority() -> None:
    """from_dict() should parse priority field from dict."""
    todo = Todo.from_dict({"id": 1, "text": "x", "priority": 5})
    assert todo.priority == 5


def test_todo_from_dict_priority_defaults_to_zero() -> None:
    """from_dict() should default priority to 0 when not present."""
    todo = Todo.from_dict({"id": 1, "text": "x"})
    assert todo.priority == 0


def test_todo_to_dict_includes_priority() -> None:
    """to_dict() should include priority in output."""
    todo = Todo(id=1, text="test", priority=3)
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 3


def test_todo_to_dict_includes_default_priority() -> None:
    """to_dict() should include priority even when using default value."""
    todo = Todo(id=1, text="test")
    result = todo.to_dict()
    assert "priority" in result
    assert result["priority"] == 0


def test_todo_priority_roundtrip() -> None:
    """Priority should survive a to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="test", priority=7)
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.priority == 7


def test_todo_from_dict_validates_priority_type() -> None:
    """from_dict() should accept valid integer priority values."""
    # Integer priority should work
    todo = Todo.from_dict({"id": 1, "text": "x", "priority": 10})
    assert todo.priority == 10

    # Zero should work
    todo = Todo.from_dict({"id": 1, "text": "x", "priority": 0})
    assert todo.priority == 0

    # Negative should work (lower = higher priority in Unix convention)
    todo = Todo.from_dict({"id": 1, "text": "x", "priority": -1})
    assert todo.priority == -1
