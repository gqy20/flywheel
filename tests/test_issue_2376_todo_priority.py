"""Tests for Todo priority field (Issue #2376).

These tests verify that:
1. Todo has priority field (int 1-4, default 2 for medium)
2. set_priority(value: int) validates range and raises ValueError if invalid
3. from_dict validates priority is 1-4, uses default 2 if missing
4. Todo.__repr__ includes priority field
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_with_high_priority() -> None:
    """Todo with priority=1 (high) should store correctly."""
    todo = Todo(id=1, text="urgent task", priority=1)
    assert todo.priority == 1


def test_todo_without_priority_defaults_to_medium() -> None:
    """Todo without priority should default to 2 (medium)."""
    todo = Todo(id=1, text="normal task")
    assert todo.priority == 2


def test_todo_with_all_priority_levels() -> None:
    """Todo should accept all valid priority levels (1-4)."""
    for level in [1, 2, 3, 4]:
        todo = Todo(id=level, text=f"task {level}", priority=level)
        assert todo.priority == level


def test_set_priority_valid_values() -> None:
    """set_priority should accept valid priority values (1-4)."""
    todo = Todo(id=1, text="task", priority=2)
    original_updated_at = todo.updated_at

    todo.set_priority(1)
    assert todo.priority == 1
    assert todo.updated_at >= original_updated_at


def test_set_priority_rejects_zero() -> None:
    """set_priority(0) should raise ValueError."""
    todo = Todo(id=1, text="task", priority=2)
    original_updated_at = todo.updated_at

    with pytest.raises(ValueError, match="Priority must be between 1 and 4"):
        todo.set_priority(0)

    # Verify state unchanged after failed validation
    assert todo.priority == 2
    assert todo.updated_at == original_updated_at


def test_set_priority_rejects_five() -> None:
    """set_priority(5) should raise ValueError."""
    todo = Todo(id=1, text="task", priority=2)
    original_updated_at = todo.updated_at

    with pytest.raises(ValueError, match="Priority must be between 1 and 4"):
        todo.set_priority(5)

    # Verify state unchanged after failed validation
    assert todo.priority == 2
    assert todo.updated_at == original_updated_at


def test_set_priority_rejects_negative() -> None:
    """set_priority(-1) should raise ValueError."""
    todo = Todo(id=1, text="task", priority=2)

    with pytest.raises(ValueError, match="Priority must be between 1 and 4"):
        todo.set_priority(-1)


def test_from_dict_with_valid_priority() -> None:
    """from_dict should accept valid priority values."""
    data = {"id": 1, "text": "task", "priority": 3}
    todo = Todo.from_dict(data)
    assert todo.priority == 3


def test_from_dict_without_priority_defaults_to_medium() -> None:
    """from_dict should default to priority=2 when missing."""
    data = {"id": 1, "text": "task"}
    todo = Todo.from_dict(data)
    assert todo.priority == 2


def test_from_dict_rejects_invalid_priority_zero() -> None:
    """from_dict should reject priority=0."""
    data = {"id": 1, "text": "task", "priority": 0}
    with pytest.raises(ValueError, match=r"must be between 1 and 4"):
        Todo.from_dict(data)


def test_from_dict_rejects_invalid_priority_five() -> None:
    """from_dict should reject priority=5."""
    data = {"id": 1, "text": "task", "priority": 5}
    with pytest.raises(ValueError, match=r"must be between 1 and 4"):
        Todo.from_dict(data)


def test_from_dict_rejects_invalid_priority_negative() -> None:
    """from_dict should reject negative priority."""
    data = {"id": 1, "text": "task", "priority": -1}
    with pytest.raises(ValueError, match=r"must be between 1 and 4"):
        Todo.from_dict(data)


def test_from_dict_rejects_invalid_priority_string() -> None:
    """from_dict should reject string priority."""
    data = {"id": 1, "text": "task", "priority": "high"}
    with pytest.raises(ValueError, match=r"must be an integer between 1 and 4"):
        Todo.from_dict(data)


def test_repr_includes_priority() -> None:
    """Todo.__repr__ should include priority field."""
    todo = Todo(id=1, text="task", priority=1)
    result = repr(todo)
    assert "priority=1" in result


def test_repr_with_default_priority() -> None:
    """Todo.__repr__ should show default priority when not specified."""
    todo = Todo(id=1, text="task")
    result = repr(todo)
    assert "priority=2" in result


def test_to_dict_includes_priority() -> None:
    """Todo.to_dict() should include priority field."""
    todo = Todo(id=1, text="task", priority=3)
    data = todo.to_dict()
    assert data["priority"] == 3


def test_to_dict_from_dict_roundtrip_preserves_priority() -> None:
    """Priority should be preserved through to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="task", priority=4)
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.priority == 4
