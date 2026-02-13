"""Tests for Todo.__eq__ and __hash__ methods (Issue #3030).

This module tests that Todo objects can be compared for equality based on id,
and can be used in sets/dicts for deduplication.
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todos_with_same_id_are_equal(self) -> None:
        """Two Todo objects with the same id should be equal."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")
        assert todo1 == todo2

    def test_todos_with_different_id_are_not_equal(self) -> None:
        """Two Todo objects with different ids should not be equal."""
        todo1 = Todo(id=1, text="same text")
        todo2 = Todo(id=2, text="same text")
        assert todo1 != todo2

    def test_todo_equals_self(self) -> None:
        """A Todo object should equal itself."""
        todo = Todo(id=1, text="test")
        assert todo == todo

    def test_todo_not_equal_to_non_todo(self) -> None:
        """A Todo should not be equal to a non-Todo object."""
        todo = Todo(id=1, text="test")
        assert todo != "not a todo"
        assert todo != 1
        assert todo != {"id": 1, "text": "test"}
        assert todo is not None


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todos_with_same_id_have_same_hash(self) -> None:
        """Two Todo objects with the same id should have the same hash."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")
        assert hash(todo1) == hash(todo2)

    def test_todos_with_different_id_have_different_hash(self) -> None:
        """Two Todo objects with different ids should have different hashes."""
        todo1 = Todo(id=1, text="same")
        todo2 = Todo(id=2, text="same")
        # Note: hash collisions are theoretically possible but unlikely
        assert hash(todo1) != hash(todo2)


class TestTodoSetOperations:
    """Tests for using Todo in sets."""

    def test_set_deduplicates_by_id(self) -> None:
        """A set should deduplicate Todo objects by id."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")
        todo3 = Todo(id=2, text="c")

        unique_todos = {todo1, todo2, todo3}
        assert len(unique_todos) == 2

    def test_set_accepts_single_todo(self) -> None:
        """A single Todo should be usable in a set."""
        todo = Todo(id=1, text="test")
        unique_todos = {todo}
        assert len(unique_todos) == 1
        assert todo in unique_todos

    def test_set_membership_by_id(self) -> None:
        """Set membership should work based on id equality."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")

        todo_set = {todo1}
        assert todo2 in todo_set


class TestTodoDictKeyOperations:
    """Tests for using Todo as dict keys."""

    def test_dict_key_deduplicates_by_id(self) -> None:
        """Dict should use Todo id for key equality."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")

        d = {todo1: "first"}
        d[todo2] = "second"

        assert len(d) == 1
        assert d[todo1] == "second"

    def test_dict_lookup_by_id(self) -> None:
        """Dict lookup should work based on id equality."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")

        d = {todo1: "value"}
        assert d[todo2] == "value"
