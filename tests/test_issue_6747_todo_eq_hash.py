"""Tests for Todo.__eq__ and __hash__ methods (Issue #6747).

These tests verify that:
1. Todo objects with the same id are considered equal
2. Todo objects with different ids are not equal
3. Todo objects can be used in sets (hashable)
4. Todo objects can be used as dict keys (hashable)
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEq:
    """Tests for Todo.__eq__ method."""

    def test_todos_with_same_id_are_equal(self) -> None:
        """Two Todo objects with the same id should be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="different text", done=True)

        assert todo1 == todo2

    def test_todos_with_different_id_are_not_equal(self) -> None:
        """Two Todo objects with different ids should not be equal."""
        todo1 = Todo(id=1, text="same text", done=False)
        todo2 = Todo(id=2, text="same text", done=False)

        assert todo1 != todo2

    def test_todo_not_equal_to_non_todo(self) -> None:
        """A Todo should not be equal to a non-Todo object."""
        todo = Todo(id=1, text="task")

        assert todo != 1
        assert todo != "task"
        assert todo != {"id": 1, "text": "task"}
        assert todo != None  # noqa: E711

    def test_todo_equal_to_itself(self) -> None:
        """A Todo should be equal to itself (reflexivity)."""
        todo = Todo(id=1, text="task")

        assert todo == todo


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todos_with_same_id_have_same_hash(self) -> None:
        """Two Todo objects with the same id should have the same hash."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="different text", done=True)

        assert hash(todo1) == hash(todo2)

    def test_todos_with_different_id_have_different_hash(self) -> None:
        """Two Todo objects with different ids should have different hashes."""
        todo1 = Todo(id=1, text="same text", done=False)
        todo2 = Todo(id=2, text="same text", done=False)

        assert hash(todo1) != hash(todo2)

    def test_todo_can_be_used_in_set(self) -> None:
        """Todo objects should be usable in a set."""
        todo1 = Todo(id=1, text="task one")
        todo2 = Todo(id=1, text="task one updated")  # Same id, different text
        todo3 = Todo(id=2, text="task two")

        todo_set = {todo1, todo2, todo3}

        # Should have only 2 items due to deduplication by id
        assert len(todo_set) == 2

    def test_todo_can_be_used_as_dict_key(self) -> None:
        """Todo objects should be usable as dictionary keys."""
        todo1 = Todo(id=1, text="task one")
        todo2 = Todo(id=1, text="task one updated")  # Same id
        todo3 = Todo(id=2, text="task two")

        todo_dict = {todo1: "first", todo2: "second", todo3: "third"}

        # Should have only 2 keys due to deduplication by id
        assert len(todo_dict) == 2
        # The second value should have overwritten the first for id=1
        assert todo_dict[todo1] == "second"
