"""Tests for Todo priority field (Issue #6857).

These tests verify that:
1. Todo dataclass includes priority field with default value 0
2. from_dict correctly parses and validates priority field (only 0/1/2)
3. to_dict serializes the priority field
4. Existing tests are not affected
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoPriorityDefault:
    """Tests for Todo priority default value."""

    def test_todo_default_priority_is_zero(self) -> None:
        """Todo should have default priority of 0 (normal)."""
        todo = Todo(id=1, text="buy milk")
        assert todo.priority == 0

    def test_todo_priority_can_be_set(self) -> None:
        """Todo priority can be explicitly set to valid values."""
        todo_high = Todo(id=1, text="urgent task", priority=1)
        assert todo_high.priority == 1

        todo_low = Todo(id=2, text="later task", priority=2)
        assert todo_low.priority == 2

        todo_normal = Todo(id=3, text="normal task", priority=0)
        assert todo_normal.priority == 0


class TestTodoPriorityFromDict:
    """Tests for from_dict priority parsing and validation."""

    def test_from_dict_parses_valid_priority_zero(self) -> None:
        """from_dict should correctly parse priority=0."""
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": 0})
        assert todo.priority == 0

    def test_from_dict_parses_valid_priority_one(self) -> None:
        """from_dict should correctly parse priority=1 (high)."""
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": 1})
        assert todo.priority == 1

    def test_from_dict_parses_valid_priority_two(self) -> None:
        """from_dict should correctly parse priority=2 (low)."""
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": 2})
        assert todo.priority == 2

    def test_from_dict_default_priority_when_missing(self) -> None:
        """from_dict should use default priority=0 when not specified."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.priority == 0

    def test_from_dict_rejects_invalid_priority_three(self) -> None:
        """from_dict should reject priority=3 (invalid)."""
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "task", "priority": 3})

    def test_from_dict_rejects_invalid_priority_negative(self) -> None:
        """from_dict should reject negative priority values."""
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "task", "priority": -1})

    def test_from_dict_rejects_invalid_priority_string(self) -> None:
        """from_dict should reject non-integer priority values."""
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "task", "priority": "high"})


class TestTodoPriorityToDict:
    """Tests for to_dict priority serialization."""

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include priority field."""
        todo = Todo(id=1, text="task", priority=1)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 1

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict should include default priority=0."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()
        assert data["priority"] == 0


class TestTodoPriorityRoundTrip:
    """Tests for priority field round-trip through dict."""

    def test_roundtrip_preserves_priority_high(self) -> None:
        """Round-trip through dict should preserve priority=1."""
        original = Todo(id=1, text="urgent", priority=1)
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.priority == 1

    def test_roundtrip_preserves_priority_low(self) -> None:
        """Round-trip through dict should preserve priority=2."""
        original = Todo(id=1, text="later", priority=2)
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.priority == 2

    def test_roundtrip_preserves_priority_normal(self) -> None:
        """Round-trip through dict should preserve priority=0."""
        original = Todo(id=1, text="normal", priority=0)
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.priority == 0
