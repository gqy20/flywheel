"""Regression tests for issue #6189: Todo.__eq__ and __hash__ support.

This module tests that:
1. Two Todo objects with the same id are equal (== returns True)
2. Todo objects can be placed in a set and deduplicated by id
3. hash(todo) == hash(todo.id)
"""

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todos_with_same_id_are_equal(self) -> None:
        """Two Todo objects with the same id should be equal."""
        todo1 = Todo(id=1, text="Buy groceries")
        todo2 = Todo(id=1, text="Different text")
        assert todo1 == todo2

    def test_todos_with_different_id_are_not_equal(self) -> None:
        """Two Todo objects with different ids should not be equal."""
        todo1 = Todo(id=1, text="Same text")
        todo2 = Todo(id=2, text="Same text")
        assert todo1 != todo2

    def test_todo_equality_with_done_flag(self) -> None:
        """Equality should be based on id only, ignoring done flag."""
        todo1 = Todo(id=1, text="Task", done=False)
        todo2 = Todo(id=1, text="Task", done=True)
        assert todo1 == todo2


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todo_is_hashable(self) -> None:
        """Todo objects should be hashable (no TypeError raised)."""
        todo = Todo(id=1, text="Test")
        # Should not raise TypeError
        _ = hash(todo)

    def test_todo_hash_matches_id_hash(self) -> None:
        """hash(todo) should equal hash(todo.id)."""
        todo = Todo(id=42, text="Test task")
        assert hash(todo) == hash(todo.id)

    def test_todos_with_same_id_have_same_hash(self) -> None:
        """Two Todo objects with the same id should have the same hash."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=1, text="Second")
        assert hash(todo1) == hash(todo2)


class TestTodoSetOperations:
    """Tests for Todo in set operations."""

    def test_todos_deduplicate_by_id_in_set(self) -> None:
        """Set should deduplicate Todo objects by id."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=1, text="Second")  # Same id, different text
        todo_set = {todo1, todo2}
        assert len(todo_set) == 1

    def test_multiple_todos_in_set(self) -> None:
        """Set can contain multiple Todo objects with different ids."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=2, text="Second")
        todo3 = Todo(id=3, text="Third")
        todo_set = {todo1, todo2, todo3}
        assert len(todo_set) == 3

    def test_todo_set_membership_by_id(self) -> None:
        """Set membership should work based on id."""
        todo1 = Todo(id=1, text="Original")
        todo_set = {todo1}
        # Different object with same id should be "in" the set
        todo2 = Todo(id=1, text="Different")
        assert todo2 in todo_set


class TestTodoDictKey:
    """Tests for using Todo as dict key."""

    def test_todo_as_dict_key(self) -> None:
        """Todo can be used as a dictionary key."""
        todo1 = Todo(id=1, text="Key")
        d = {todo1: "value"}
        # Different object with same id should access the same value
        todo2 = Todo(id=1, text="Different")
        assert d[todo2] == "value"
