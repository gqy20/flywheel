"""Tests for Todo comparison capabilities (Issue #5916).

These tests verify that:
1. Todo objects can be compared for equality (__eq__)
2. Todo objects can be sorted (__lt__)
3. Todo objects can be hashed and used in sets/dicts (__hash__)
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todo_equality_same_values(self) -> None:
        """Two Todos with same id, text, and done should be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)
        assert todo1 == todo2

    def test_todo_equality_different_id(self) -> None:
        """Two Todos with different ids should not be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy milk", done=False)
        assert todo1 != todo2

    def test_todo_equality_different_text(self) -> None:
        """Two Todos with different text should not be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy bread", done=False)
        assert todo1 != todo2

    def test_todo_equality_different_done(self) -> None:
        """Two Todos with different done status should not be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=True)
        assert todo1 != todo2

    def test_todo_equality_same_instance(self) -> None:
        """A Todo should be equal to itself."""
        todo = Todo(id=1, text="buy milk", done=False)
        assert todo == todo

    def test_todo_equality_not_todo(self) -> None:
        """A Todo should not be equal to a non-Todo object."""
        todo = Todo(id=1, text="buy milk", done=False)
        assert todo != "not a todo"
        assert todo != 1
        assert todo != {"id": 1, "text": "buy milk", "done": False}


class TestTodoOrdering:
    """Tests for Todo.__lt__ method."""

    def test_todo_lt_by_id(self) -> None:
        """Todos should be comparable by id for ordering."""
        todo1 = Todo(id=1, text="first", done=False)
        todo2 = Todo(id=2, text="second", done=False)
        assert todo1 < todo2
        assert not todo2 < todo1

    def test_todo_gt_by_id(self) -> None:
        """Todos should support greater than comparison."""
        todo1 = Todo(id=1, text="first", done=False)
        todo2 = Todo(id=2, text="second", done=False)
        assert todo2 > todo1
        assert not todo1 > todo2

    def test_todo_le_by_id(self) -> None:
        """Todos should support less than or equal comparison."""
        todo1 = Todo(id=1, text="first", done=False)
        todo2 = Todo(id=1, text="different", done=False)
        todo3 = Todo(id=2, text="second", done=False)
        assert todo1 <= todo2  # Same id
        assert todo1 <= todo3  # Different id

    def test_todo_ge_by_id(self) -> None:
        """Todos should support greater than or equal comparison."""
        todo1 = Todo(id=1, text="first", done=False)
        todo2 = Todo(id=1, text="different", done=False)
        todo3 = Todo(id=2, text="second", done=False)
        assert todo2 >= todo1  # Same id
        assert todo3 >= todo1  # Different id

    def test_todo_sorted_by_id(self) -> None:
        """A list of Todos should be sortable by id."""
        todos = [
            Todo(id=3, text="third", done=False),
            Todo(id=1, text="first", done=False),
            Todo(id=2, text="second", done=False),
        ]
        sorted_todos = sorted(todos)
        assert sorted_todos[0].id == 1
        assert sorted_todos[1].id == 2
        assert sorted_todos[2].id == 3


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todo_hashable(self) -> None:
        """Todo objects should be hashable."""
        todo = Todo(id=1, text="buy milk", done=False)
        # Should not raise TypeError
        hash(todo)

    def test_todo_in_set(self) -> None:
        """Todo objects should be usable in a set."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy bread", done=False)
        todo_set = {todo1, todo2}
        assert len(todo_set) == 2
        assert todo1 in todo_set
        assert todo2 in todo_set

    def test_todo_in_dict_key(self) -> None:
        """Todo objects should be usable as dictionary keys."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy bread", done=False)
        todo_dict = {todo1: "first", todo2: "second"}
        assert todo_dict[todo1] == "first"
        assert todo_dict[todo2] == "second"

    def test_todo_set_deduplication(self) -> None:
        """Equal Todo objects should deduplicate in a set."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)
        todo_set = {todo1, todo2}
        # Equal todos should be deduplicated
        assert len(todo_set) == 1

    def test_todo_hash_consistency(self) -> None:
        """Equal Todos should have the same hash."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)
        assert hash(todo1) == hash(todo2)
