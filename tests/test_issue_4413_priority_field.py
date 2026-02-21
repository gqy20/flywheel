"""Tests for Todo priority field (issue #4413)."""

import pytest

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Test priority field in Todo dataclass."""

    def test_todo_with_priority_1(self) -> None:
        """Test creating Todo with high priority (1)."""
        todo = Todo(id=1, text="High priority task", priority=1)
        assert todo.priority == 1

    def test_todo_with_priority_2(self) -> None:
        """Test creating Todo with medium priority (2)."""
        todo = Todo(id=1, text="Medium priority task", priority=2)
        assert todo.priority == 2

    def test_todo_with_priority_3(self) -> None:
        """Test creating Todo with low priority (3)."""
        todo = Todo(id=1, text="Low priority task", priority=3)
        assert todo.priority == 3

    def test_todo_default_priority_is_2(self) -> None:
        """Test that default priority is 2 (medium)."""
        todo = Todo(id=1, text="Task")
        assert todo.priority == 2

    def test_from_dict_with_valid_priority(self) -> None:
        """Test from_dict with valid priority."""
        data = {"id": 1, "text": "Task", "priority": 1}
        todo = Todo.from_dict(data)
        assert todo.priority == 1

    def test_from_dict_without_priority_uses_default(self) -> None:
        """Test from_dict uses default priority when not provided."""
        data = {"id": 1, "text": "Task"}
        todo = Todo.from_dict(data)
        assert todo.priority == 2

    def test_from_dict_rejects_priority_0(self) -> None:
        """Test from_dict rejects priority 0 (out of range)."""
        data = {"id": 1, "text": "Task", "priority": 0}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_from_dict_rejects_priority_4(self) -> None:
        """Test from_dict rejects priority 4 (out of range)."""
        data = {"id": 1, "text": "Task", "priority": 4}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_from_dict_rejects_negative_priority(self) -> None:
        """Test from_dict rejects negative priority."""
        data = {"id": 1, "text": "Task", "priority": -1}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_from_dict_rejects_non_integer_priority(self) -> None:
        """Test from_dict rejects non-integer priority."""
        data = {"id": 1, "text": "Task", "priority": "high"}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_to_dict_includes_priority(self) -> None:
        """Test to_dict includes priority field."""
        todo = Todo(id=1, text="Task", priority=1)
        data = todo.to_dict()
        assert data["priority"] == 1

    def test_to_dict_includes_default_priority(self) -> None:
        """Test to_dict includes default priority."""
        todo = Todo(id=1, text="Task")
        data = todo.to_dict()
        assert data["priority"] == 2


class TestTodoPriorityValidation:
    """Test priority validation edge cases."""

    def test_from_dict_accepts_priority_as_string_1(self) -> None:
        """Test from_dict accepts string '1' for priority."""
        data = {"id": 1, "text": "Task", "priority": "1"}
        todo = Todo.from_dict(data)
        assert todo.priority == 1

    def test_from_dict_accepts_priority_as_string_3(self) -> None:
        """Test from_dict accepts string '3' for priority."""
        data = {"id": 1, "text": "Task", "priority": "3"}
        todo = Todo.from_dict(data)
        assert todo.priority == 3

    def test_from_dict_rejects_string_priority_out_of_range(self) -> None:
        """Test from_dict rejects string '0' for priority."""
        data = {"id": 1, "text": "Task", "priority": "0"}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)
