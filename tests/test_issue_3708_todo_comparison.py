"""Tests for Todo comparison and hashing (issue #3708).

This module tests the __eq__, __lt__, and __hash__ methods on the Todo class.
"""

import pytest

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ functionality."""

    def test_todo_equality_same_id(self) -> None:
        """Todos with same id and text should be equal."""
        todo1 = Todo(id=1, text="Buy milk", created_at="2024-01-01", updated_at="2024-01-01")
        todo2 = Todo(id=1, text="Buy milk", created_at="2024-01-02", updated_at="2024-01-02")
        assert todo1 == todo2

    def test_todo_equality_different_id(self) -> None:
        """Todos with different id should not be equal."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy milk")
        assert todo1 != todo2

    def test_todo_equality_different_text(self) -> None:
        """Todos with same id but different text should not be equal."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")
        assert todo1 != todo2

    def test_todo_equality_with_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="Buy milk")
        assert todo != "Buy milk"
        assert todo != 1
        assert todo != {"id": 1, "text": "Buy milk"}


class TestTodoOrdering:
    """Tests for Todo.__lt__ functionality."""

    def test_todo_ordering_by_id(self) -> None:
        """Todos should be sortable by id."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=2, text="Second")
        todo3 = Todo(id=3, text="Third")
        todos = [todo3, todo1, todo2]
        sorted_todos = sorted(todos)
        assert sorted_todos == [todo1, todo2, todo3]

    def test_todo_ordering_less_than(self) -> None:
        """Todo with lower id should be less than Todo with higher id."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=2, text="Second")
        assert todo1 < todo2
        assert not todo2 < todo1

    def test_todo_ordering_greater_than(self) -> None:
        """Todo with higher id should be greater than Todo with lower id."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=2, text="Second")
        assert todo2 > todo1
        assert not todo1 > todo2

    def test_todo_ordering_less_equal(self) -> None:
        """Todo __le__ should work correctly."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=1, text="First")
        todo3 = Todo(id=2, text="Second")
        assert todo1 <= todo2
        assert todo1 <= todo3

    def test_todo_ordering_greater_equal(self) -> None:
        """Todo __ge__ should work correctly."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=1, text="First")
        todo3 = Todo(id=2, text="Second")
        assert todo2 >= todo1
        assert todo3 >= todo1


class TestTodoHash:
    """Tests for Todo.__hash__ functionality."""

    def test_todo_hash_consistent(self) -> None:
        """Same Todo should produce consistent hash."""
        todo = Todo(id=1, text="Buy milk", created_at="2024-01-01", updated_at="2024-01-01")
        assert hash(todo) == hash(todo)

    def test_todo_hash_same_for_equal_todos(self) -> None:
        """Equal Todos should have same hash."""
        todo1 = Todo(id=1, text="Buy milk", created_at="2024-01-01", updated_at="2024-01-01")
        todo2 = Todo(id=1, text="Buy milk", created_at="2024-01-02", updated_at="2024-01-02")
        assert hash(todo1) == hash(todo2)

    def test_todo_hash_different_for_different_id(self) -> None:
        """Todos with different id should have different hashes."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy milk")
        assert hash(todo1) != hash(todo2)

    def test_todo_hash_usable_in_set(self) -> None:
        """Todos should be usable in sets."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy milk")  # Same id/text
        todo3 = Todo(id=2, text="Buy bread")
        todo_set = {todo1, todo2, todo3}
        assert len(todo_set) == 2
        assert todo1 in todo_set
        assert todo3 in todo_set

    def test_todo_hash_usable_as_dict_key(self) -> None:
        """Todos should be usable as dictionary keys."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy milk")  # Same id/text
        todo_dict = {todo1: "first_value"}
        todo_dict[todo2] = "second_value"
        assert len(todo_dict) == 1
        assert todo_dict[todo1] == "second_value"
