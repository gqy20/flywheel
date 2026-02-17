"""Tests for Todo priority field (Issue #3980).

These tests verify that:
1. Todo dataclass includes priority: int field with default value 0
2. from_dict() correctly parses data with priority, defaults to 0 when missing
3. to_dict() output includes priority field
4. Backward compatibility is maintained
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_create_with_priority() -> None:
    """Todo(id=1, text='a', priority=3) should create correctly."""
    todo = Todo(id=1, text="a", priority=3)

    assert todo.id == 1
    assert todo.text == "a"
    assert todo.priority == 3


def test_todo_priority_defaults_to_zero() -> None:
    """Todo without priority should default to 0."""
    todo = Todo(id=1, text="a")

    assert todo.priority == 0


def test_from_dict_with_priority() -> None:
    """from_dict({'id':1,'text':'a','priority':2}) returns correct priority."""
    data = {"id": 1, "text": "a", "priority": 2}
    todo = Todo.from_dict(data)

    assert todo.priority == 2


def test_from_dict_without_priority_defaults_to_zero() -> None:
    """from_dict({'id':1,'text':'a'}) returns priority=0."""
    data = {"id": 1, "text": "a"}
    todo = Todo.from_dict(data)

    assert todo.priority == 0


def test_to_dict_includes_priority() -> None:
    """to_dict() output should include priority field."""
    todo = Todo(id=1, text="a", priority=5)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 5


def test_to_dict_includes_default_priority() -> None:
    """to_dict() should include priority even when using default value."""
    todo = Todo(id=1, text="a")
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 0


def test_backward_compatibility() -> None:
    """Existing tests should still pass (backward compatibility)."""
    # Create todo without priority
    todo = Todo(id=1, text="backward compat test", done=False)

    # Essential fields should work as before
    assert todo.id == 1
    assert todo.text == "backward compat test"
    assert todo.done is False
    assert todo.created_at != ""
    assert todo.updated_at != ""
    assert todo.priority == 0  # New field defaults to 0


def test_from_dict_roundtrip_with_priority() -> None:
    """from_dict(to_dict()) roundtrip should preserve priority."""
    original = Todo(id=1, text="roundtrip test", priority=7)
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.priority == original.priority
