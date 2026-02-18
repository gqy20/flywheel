"""Tests for Todo priority field (Issue #4091).

These tests verify that:
1. Todo objects have an optional priority field (default 0)
2. from_dict correctly parses priority field, defaulting to 0 when missing
3. to_dict includes priority field
4. Old data files (without priority field) can still be loaded
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_default_priority_is_zero() -> None:
    """Todo created without priority should default to 0."""
    todo = Todo(id=1, text="test task")
    assert todo.priority == 0


def test_todo_can_set_priority() -> None:
    """Todo should accept explicit priority values."""
    # High priority
    todo_high = Todo(id=1, text="urgent task", priority=1)
    assert todo_high.priority == 1

    # Low priority
    todo_low = Todo(id=2, text="low priority task", priority=-1)
    assert todo_low.priority == -1


def test_from_dict_parses_priority() -> None:
    """from_dict should correctly parse priority field."""
    todo = Todo.from_dict({"id": 1, "text": "test", "priority": 1})
    assert todo.priority == 1


def test_from_dict_defaults_priority_to_zero_when_missing() -> None:
    """from_dict should default priority to 0 when field is missing (old data compatibility)."""
    todo = Todo.from_dict({"id": 1, "text": "old task"})
    assert todo.priority == 0


def test_to_dict_includes_priority() -> None:
    """to_dict should include the priority field."""
    todo = Todo(id=1, text="test", priority=1)
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 1


def test_to_dict_includes_default_priority() -> None:
    """to_dict should include priority field even when using default value."""
    todo = Todo(id=1, text="test")
    result = todo.to_dict()

    assert "priority" in result
    assert result["priority"] == 0


def test_roundtrip_preserves_priority() -> None:
    """to_dict -> from_dict should preserve priority value."""
    original = Todo(id=1, text="test", priority=1, done=True)
    roundtrip = Todo.from_dict(original.to_dict())

    assert roundtrip.priority == original.priority


def test_old_data_without_priority_loads_successfully() -> None:
    """Simulating loading old JSON data without priority field should work."""
    # This simulates data from before the priority feature was added
    old_data = {"id": 1, "text": "legacy task", "done": False}

    todo = Todo.from_dict(old_data)

    assert todo.id == 1
    assert todo.text == "legacy task"
    assert todo.done is False
    assert todo.priority == 0
