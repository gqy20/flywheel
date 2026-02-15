"""Tests for Todo priority field (Issue #3505).

These tests verify that:
1. Todo supports optional priority field with default value 1 (medium)
2. Priority values are validated to be 0 (high), 1 (medium), or 2 (low)
3. to_dict includes priority field
4. from_dict parses priority field with validation
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for the priority field on Todo."""

    def test_todo_has_priority_field_with_default(self) -> None:
        """Todo should have a priority field with default value 1 (medium)."""
        todo = Todo(id=1, text="test task")
        assert hasattr(todo, "priority")
        assert todo.priority == 1

    def test_todo_priority_can_be_set_to_high(self) -> None:
        """Todo priority=0 should represent high priority."""
        todo = Todo(id=1, text="urgent task", priority=0)
        assert todo.priority == 0

    def test_todo_priority_can_be_set_to_low(self) -> None:
        """Todo priority=2 should represent low priority."""
        todo = Todo(id=1, text="low priority task", priority=2)
        assert todo.priority == 2

    def test_todo_to_dict_includes_priority(self) -> None:
        """to_dict should include the priority field."""
        todo = Todo(id=1, text="test", priority=0)
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 0

    def test_todo_to_dict_includes_default_priority(self) -> None:
        """to_dict should include priority field even when using default."""
        todo = Todo(id=1, text="test")
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 1

    def test_from_dict_parses_priority(self) -> None:
        """from_dict should parse priority field correctly."""
        todo = Todo.from_dict({"id": 1, "text": "test", "priority": 2})
        assert todo.priority == 2

    def test_from_dict_defaults_priority_to_medium(self) -> None:
        """from_dict should default priority to 1 if not provided."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.priority == 1

    def test_from_dict_validates_priority_range_high(self) -> None:
        """from_dict should reject priority values outside 0-2 range."""
        import pytest

        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "test", "priority": 5})

    def test_from_dict_validates_priority_range_negative(self) -> None:
        """from_dict should reject negative priority values."""
        import pytest

        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "test", "priority": -1})

    def test_from_dict_validates_priority_type(self) -> None:
        """from_dict should reject non-integer priority values."""
        import pytest

        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "test", "priority": "high"})

    def test_from_dict_accepts_zero_and_one_priority(self) -> None:
        """from_dict should accept 0 and 1 as valid priority values."""
        todo0 = Todo.from_dict({"id": 1, "text": "test", "priority": 0})
        todo1 = Todo.from_dict({"id": 2, "text": "test", "priority": 1})
        assert todo0.priority == 0
        assert todo1.priority == 1

    def test_round_trip_preserves_priority(self) -> None:
        """to_dict -> from_dict round trip should preserve priority."""
        original = Todo(id=1, text="test", priority=0)
        roundtrip = Todo.from_dict(original.to_dict())
        assert roundtrip.priority == 0
