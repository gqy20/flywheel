"""Tests for Todo comparison methods (Issue #5916).

These tests verify that:
1. Todo objects can be compared for equality (__eq__)
2. Todo objects can be sorted by id (__lt__)
3. Todo objects can be placed in sets/dicts (__hash__)
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_equal_todos_with_same_id_text_done(self) -> None:
        """Two todos with same id, text, and done status should be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
        todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
        assert todo1 == todo2

    def test_equal_todos_ignoring_timestamps(self) -> None:
        """Todos with same id, text, done should be equal even with different timestamps."""
        todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
        todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-02T00:00:00+00:00", updated_at="2024-01-02T00:00:00+00:00")
        assert todo1 == todo2

    def test_unequal_todos_different_id(self) -> None:
        """Todos with different ids should not be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy milk", done=False)
        assert todo1 != todo2

    def test_unequal_todos_different_text(self) -> None:
        """Todos with different text should not be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy bread", done=False)
        assert todo1 != todo2

    def test_unequal_todos_different_done(self) -> None:
        """Todos with different done status should not be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=True)
        assert todo1 != todo2

    def test_equality_with_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="buy milk", done=False)
        assert todo != "Todo(id=1, text='buy milk', done=False)"
        assert todo != 1
        assert todo != {"id": 1, "text": "buy milk", "done": False}


class TestTodoOrdering:
    """Tests for Todo.__lt__ method."""

    def test_sort_todos_by_id(self) -> None:
        """Todos should be sortable by id."""
        todo1 = Todo(id=1, text="first", done=False)
        todo2 = Todo(id=2, text="second", done=False)
        todo3 = Todo(id=3, text="third", done=False)

        unsorted = [todo3, todo1, todo2]
        sorted_todos = sorted(unsorted)

        assert sorted_todos[0].id == 1
        assert sorted_todos[1].id == 2
        assert sorted_todos[2].id == 3

    def test_less_than_comparison(self) -> None:
        """Todo with lower id should be 'less than' todo with higher id."""
        todo1 = Todo(id=1, text="first", done=False)
        todo2 = Todo(id=2, text="second", done=False)
        assert todo1 < todo2
        assert not todo2 < todo1

    def test_greater_than_comparison(self) -> None:
        """Todo with higher id should be 'greater than' todo with lower id."""
        todo1 = Todo(id=1, text="first", done=False)
        todo2 = Todo(id=2, text="second", done=False)
        assert todo2 > todo1
        assert not todo1 > todo2

    def test_less_than_or_equal_comparison(self) -> None:
        """Todo with lower or equal id should be 'less than or equal'."""
        todo1 = Todo(id=1, text="first", done=False)
        todo2 = Todo(id=2, text="second", done=False)
        todo3 = Todo(id=1, text="first copy", done=False)

        assert todo1 <= todo2
        assert todo1 <= todo3

    def test_greater_than_or_equal_comparison(self) -> None:
        """Todo with higher or equal id should be 'greater than or equal'."""
        todo1 = Todo(id=1, text="first", done=False)
        todo2 = Todo(id=2, text="second", done=False)
        todo3 = Todo(id=1, text="first copy", done=False)

        assert todo2 >= todo1
        assert todo1 >= todo3


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todo_in_set(self) -> None:
        """Todo objects should be placeable in a set without TypeError."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy bread", done=False)

        # Should not raise TypeError
        todo_set = {todo1, todo2}
        assert len(todo_set) == 2

    def test_todo_as_dict_key(self) -> None:
        """Todo objects should be usable as dictionary keys."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy bread", done=False)

        # Should not raise TypeError
        todo_dict = {todo1: "first", todo2: "second"}
        assert todo_dict[todo1] == "first"
        assert todo_dict[todo2] == "second"

    def test_equal_todos_same_hash(self) -> None:
        """Equal todos should have the same hash."""
        todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
        todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-02T00:00:00+00:00", updated_at="2024-01-02T00:00:00+00:00")

        assert hash(todo1) == hash(todo2)

    def test_set_deduplication_with_equal_todos(self) -> None:
        """Set should deduplicate equal todos."""
        todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
        todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-02T00:00:00+00:00", updated_at="2024-01-02T00:00:00+00:00")

        todo_set = {todo1, todo2}
        # Both todos are equal, so set should have only one element
        assert len(todo_set) == 1
