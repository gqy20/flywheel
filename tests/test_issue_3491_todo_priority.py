"""Tests for Todo priority field (Issue #3491).

These tests verify that:
1. Todo dataclass has priority: int = 0 field
2. from_dict() can parse priority field (defaults to 0)
3. to_dict() output includes priority
4. Priority serialization and deserialization works correctly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_priority_field_default_zero() -> None:
    """Todo should have a priority field that defaults to 0."""
    todo = Todo(id=1, text="buy milk")
    assert todo.priority == 0


def test_todo_priority_can_be_set() -> None:
    """Todo priority can be set to a custom value."""
    todo = Todo(id=1, text="x", priority=2)
    assert todo.priority == 2


def test_todo_from_dict_parses_priority() -> None:
    """from_dict() should parse priority from data."""
    todo = Todo.from_dict({"id": 1, "text": "x", "priority": 5})
    assert todo.priority == 5


def test_todo_from_dict_defaults_priority_to_zero() -> None:
    """from_dict() should default priority to 0 if not provided."""
    todo = Todo.from_dict({"id": 1, "text": "x"})
    assert todo.priority == 0


def test_todo_to_dict_includes_priority() -> None:
    """to_dict() output should include priority field."""
    todo = Todo(id=1, text="x", priority=3)
    data = todo.to_dict()

    assert "priority" in data
    assert data["priority"] == 3


def test_todo_to_dict_includes_default_priority() -> None:
    """to_dict() should include priority even when default."""
    todo = Todo(id=1, text="x")
    data = todo.to_dict()

    assert "priority" in data
    assert data["priority"] == 0


def test_todo_priority_serialization_roundtrip() -> None:
    """Priority should survive serialization roundtrip."""
    original = Todo(id=1, text="test task", priority=7, done=True)
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.priority == 7
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
