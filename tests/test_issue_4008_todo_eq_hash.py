"""Tests for Todo.__eq__ and __hash__ methods (Issue #4008).

These tests verify that:
1. Todo objects with same fields compare as equal
2. Todo objects with different fields compare as not equal
3. Todo objects can be hashed and used in sets/dicts
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEq:
    """Tests for Todo.__eq__ method."""

    def test_todo_eq_same_id_and_text(self) -> None:
        """Todo objects with same id and text (and same timestamps) should be equal."""
        todo1 = Todo(id=1, text="buy milk", created_at="2024-01-01", updated_at="2024-01-01")
        todo2 = Todo(id=1, text="buy milk", created_at="2024-01-01", updated_at="2024-01-01")
        assert todo1 == todo2

    def test_todo_eq_all_fields_match(self) -> None:
        """Todo objects with all matching fields should be equal."""
        todo1 = Todo(id=1, text="task", done=True, created_at="2024-01-01", updated_at="2024-01-02")
        todo2 = Todo(id=1, text="task", done=True, created_at="2024-01-01", updated_at="2024-01-02")
        assert todo1 == todo2

    def test_todo_neq_different_id(self) -> None:
        """Todo objects with different id should not be equal."""
        todo1 = Todo(id=1, text="buy milk")
        todo2 = Todo(id=2, text="buy milk")
        assert todo1 != todo2

    def test_todo_neq_different_text(self) -> None:
        """Todo objects with different text should not be equal."""
        todo1 = Todo(id=1, text="buy milk")
        todo2 = Todo(id=1, text="buy bread")
        assert todo1 != todo2

    def test_todo_neq_different_done(self) -> None:
        """Todo objects with different done status should not be equal."""
        todo1 = Todo(id=1, text="task", done=False)
        todo2 = Todo(id=1, text="task", done=True)
        assert todo1 != todo2

    def test_todo_eq_with_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="task")
        assert todo != "task"
        assert todo != 1
        assert todo != {"id": 1, "text": "task"}
        assert todo is not None

    def test_todo_eq_reflexive(self) -> None:
        """A Todo should be equal to itself."""
        todo = Todo(id=1, text="task")
        assert todo == todo

    def test_todo_eq_symmetric(self) -> None:
        """Equality should be symmetric (a == b implies b == a)."""
        todo1 = Todo(id=1, text="task", created_at="2024-01-01", updated_at="2024-01-01")
        todo2 = Todo(id=1, text="task", created_at="2024-01-01", updated_at="2024-01-01")
        assert todo1 == todo2
        assert todo2 == todo1


class TestTodoHash:
    """Tests for Todo.__hash__ method.

    Note: hash is based on id only, since id is expected to be unique.
    Two todos with the same id but different text/done/timestamps will
    have the same hash but may not be equal (hash collision is allowed).
    """

    def test_todo_hash_not_raises(self) -> None:
        """hash(Todo) should not raise TypeError."""
        todo = Todo(id=1, text="task")
        # This should not raise TypeError
        hash(todo)

    def test_todo_hash_same_for_same_id(self) -> None:
        """Todo objects with same id should have same hash."""
        todo1 = Todo(id=1, text="task")
        todo2 = Todo(id=1, text="task")
        assert hash(todo1) == hash(todo2)

    def test_todo_hash_different_for_different_id(self) -> None:
        """Todo objects with different id should typically have different hash."""
        todo1 = Todo(id=1, text="task")
        todo2 = Todo(id=2, text="task")
        # Hash may rarely collide, but for small integers should be different
        assert hash(todo1) != hash(todo2)

    def test_todo_in_set_by_id(self) -> None:
        """Todo objects should be usable in a set, deduplicated by id."""
        todo1 = Todo(id=1, text="task", created_at="2024-01-01", updated_at="2024-01-01")
        todo2 = Todo(id=1, text="task", created_at="2024-01-01", updated_at="2024-01-01")
        todo3 = Todo(id=2, text="other")

        todo_set = {todo1, todo2, todo3}

        # Equal todos should be deduplicated in a set
        assert len(todo_set) == 2
        assert todo1 in todo_set
        assert todo2 in todo_set
        assert todo3 in todo_set

    def test_todo_as_dict_key(self) -> None:
        """Todo objects should be usable as dict keys."""
        todo1 = Todo(id=1, text="task", created_at="2024-01-01", updated_at="2024-01-01")
        todo2 = Todo(id=1, text="task", created_at="2024-01-01", updated_at="2024-01-01")
        todo3 = Todo(id=2, text="other")

        todo_dict = {todo1: "first", todo3: "third"}

        # Equal todo should access same value
        assert todo_dict[todo2] == "first"
        assert todo_dict[todo3] == "third"
