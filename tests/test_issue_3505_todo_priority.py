"""Tests for Todo priority field (Issue #3505).

These tests verify that:
1. Todo supports an optional priority field with default value 1 (medium)
2. from_dict parses priority field and validates range (0-2)
3. to_dict includes priority field
4. Invalid priority values raise ValueError
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Test suite for Todo priority field support."""

    def test_todo_creation_with_priority(self) -> None:
        """Todo should accept priority parameter during creation."""
        todo = Todo(id=1, text="x", priority=0)
        assert todo.priority == 0

    def test_todo_priority_default_is_one(self) -> None:
        """Todo priority should default to 1 (medium)."""
        todo = Todo(id=1, text="x")
        assert todo.priority == 1

    def test_todo_priority_high(self) -> None:
        """Todo priority=0 should represent high priority."""
        todo = Todo(id=1, text="urgent task", priority=0)
        assert todo.priority == 0

    def test_todo_priority_medium(self) -> None:
        """Todo priority=1 should represent medium priority."""
        todo = Todo(id=1, text="normal task", priority=1)
        assert todo.priority == 1

    def test_todo_priority_low(self) -> None:
        """Todo priority=2 should represent low priority."""
        todo = Todo(id=1, text="low priority task", priority=2)
        assert todo.priority == 2

    def test_from_dict_with_priority_zero(self) -> None:
        """from_dict should parse priority=0 correctly."""
        todo = Todo.from_dict({"id": 1, "text": "x", "priority": 0})
        assert todo.priority == 0

    def test_from_dict_with_priority_one(self) -> None:
        """from_dict should parse priority=1 correctly."""
        todo = Todo.from_dict({"id": 1, "text": "x", "priority": 1})
        assert todo.priority == 1

    def test_from_dict_with_priority_two(self) -> None:
        """from_dict should parse priority=2 correctly."""
        todo = Todo.from_dict({"id": 1, "text": "x", "priority": 2})
        assert todo.priority == 2

    def test_from_dict_priority_defaults_to_one(self) -> None:
        """from_dict should default priority to 1 when not specified."""
        todo = Todo.from_dict({"id": 1, "text": "x"})
        assert todo.priority == 1

    def test_from_dict_invalid_priority_high_raises(self) -> None:
        """from_dict should raise ValueError for priority > 2."""
        try:
            Todo.from_dict({"id": 1, "text": "x", "priority": 5})
            assert False, "Expected ValueError for invalid priority"
        except ValueError as e:
            assert "priority" in str(e).lower()

    def test_from_dict_invalid_priority_negative_raises(self) -> None:
        """from_dict should raise ValueError for negative priority."""
        try:
            Todo.from_dict({"id": 1, "text": "x", "priority": -1})
            assert False, "Expected ValueError for negative priority"
        except ValueError as e:
            assert "priority" in str(e).lower()

    def test_from_dict_invalid_priority_string_raises(self) -> None:
        """from_dict should raise ValueError for non-integer priority."""
        try:
            Todo.from_dict({"id": 1, "text": "x", "priority": "high"})
            assert False, "Expected ValueError for non-integer priority"
        except ValueError as e:
            assert "priority" in str(e).lower()

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include priority field."""
        todo = Todo(id=1, text="x", priority=0)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 0

    def test_to_dict_priority_reflects_changes(self) -> None:
        """to_dict should reflect current priority value."""
        todo = Todo(id=1, text="x", priority=2)
        data = todo.to_dict()
        assert data["priority"] == 2

    def test_round_trip_preserves_priority(self) -> None:
        """Priority should be preserved through to_dict/from_dict cycle."""
        original = Todo(id=1, text="x", priority=0)
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.priority == original.priority

    def test_round_trip_with_all_priorities(self) -> None:
        """All valid priority values should survive round trip."""
        for priority in (0, 1, 2):
            original = Todo(id=1, text="x", priority=priority)
            data = original.to_dict()
            restored = Todo.from_dict(data)
            assert restored.priority == priority, f"Priority {priority} not preserved"
