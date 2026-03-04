"""Tests for Todo priority field (Issue #7207).

These tests verify that:
1. Todo objects support optional priority field (0=none, 1=low, 2=medium, 3=high)
2. from_dict() correctly loads old data without priority field
3. to_dict() includes priority field
4. Default priority is 0
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_with_priority_field() -> None:
    """Todo should accept a priority field during construction."""
    todo = Todo(id=1, text="high priority task", priority=3)
    assert todo.priority == 3


def test_todo_default_priority_is_zero() -> None:
    """Todo created without explicit priority should have priority=0."""
    todo = Todo(id=1, text="normal task")
    assert todo.priority == 0


def test_todo_priority_values() -> None:
    """Todo should accept priority values 0-3."""
    for priority in [0, 1, 2, 3]:
        todo = Todo(id=1, text="task", priority=priority)
        assert todo.priority == priority


def test_todo_to_dict_includes_priority() -> None:
    """to_dict() output should include priority field."""
    todo = Todo(id=1, text="task", priority=2)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 2


def test_todo_to_dict_includes_default_priority() -> None:
    """to_dict() should include priority even when using default value."""
    todo = Todo(id=1, text="task")
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 0


def test_todo_from_dict_with_priority() -> None:
    """from_dict() should correctly load data with priority field."""
    data = {"id": 1, "text": "urgent task", "priority": 3, "done": False}
    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.text == "urgent task"
    assert todo.priority == 3
    assert todo.done is False


def test_todo_from_dict_without_priority_defaults_to_zero() -> None:
    """from_dict() should set priority=0 when field is missing (backward compatibility)."""
    data = {"id": 1, "text": "legacy task", "done": True}
    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.text == "legacy task"
    assert todo.priority == 0
    assert todo.done is True


def test_todo_from_dict_with_explicit_zero_priority() -> None:
    """from_dict() should correctly handle explicit priority=0."""
    data = {"id": 1, "text": "task", "priority": 0}
    todo = Todo.from_dict(data)

    assert todo.priority == 0


def test_todo_roundtrip_preserves_priority() -> None:
    """Priority should be preserved through to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="task", priority=2, done=True)
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.priority == 2
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
