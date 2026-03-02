"""Tests for Todo __eq__ and __hash__ methods (Issue #6747).

These tests verify that:
1. Todo objects with same id are equal (regardless of other fields)
2. Todo objects with different id are not equal
3. Todo objects can be used in sets (hashable)
4. Todo objects can be used as dict keys (hashable)
5. Hash is consistent with equality
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todos_with_same_id_are_equal(self) -> None:
        """Two Todo objects with same id should be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="different text", done=True)

        assert todo1 == todo2, "Todos with same id should be equal"

    def test_todos_with_different_id_are_not_equal(self) -> None:
        """Two Todo objects with different id should not be equal."""
        todo1 = Todo(id=1, text="same text", done=False)
        todo2 = Todo(id=2, text="same text", done=False)

        assert todo1 != todo2, "Todos with different id should not be equal"

    def test_todo_equality_reflexive(self) -> None:
        """A Todo should be equal to itself."""
        todo = Todo(id=1, text="task")
        assert todo == todo

    def test_todo_equality_symmetric(self) -> None:
        """Equality should be symmetric: a == b implies b == a."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")

        assert todo1 == todo2
        assert todo2 == todo1

    def test_todo_equality_transitive(self) -> None:
        """Equality should be transitive: a == b and b == c implies a == c."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")
        todo3 = Todo(id=1, text="c")

        assert todo1 == todo2
        assert todo2 == todo3
        assert todo1 == todo3

    def test_todo_not_equal_to_non_todo(self) -> None:
        """A Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="task")

        assert todo != 1
        assert todo != "task"
        assert todo != {"id": 1, "text": "task"}
        assert todo != None


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todo_is_hashable(self) -> None:
        """Todo objects should be hashable (can call hash())."""
        todo = Todo(id=1, text="task")

        # Should not raise TypeError
        _ = hash(todo)

    def test_todo_can_be_used_in_set(self) -> None:
        """Todo objects should be usable in sets."""
        todo1 = Todo(id=1, text="task one")
        todo2 = Todo(id=2, text="task two")
        todo3 = Todo(id=1, text="same id as todo1")  # Same id as todo1

        todo_set = {todo1, todo2, todo3}

        # Set should deduplicate based on id (same id = same todo)
        assert len(todo_set) == 2, "Set should contain 2 unique todos (by id)"

    def test_todo_can_be_used_as_dict_key(self) -> None:
        """Todo objects should be usable as dictionary keys."""
        todo1 = Todo(id=1, text="task one")
        todo2 = Todo(id=2, text="task two")

        todo_dict = {todo1: "first", todo2: "second"}

        assert todo_dict[todo1] == "first"
        assert todo_dict[todo2] == "second"

    def test_hash_consistent_with_equality(self) -> None:
        """Equal todos should have equal hashes."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")

        assert todo1 == todo2
        assert hash(todo1) == hash(todo2)

    def test_hash_stable(self) -> None:
        """Hash should be stable (same object, same hash)."""
        todo = Todo(id=1, text="task")

        hash1 = hash(todo)
        hash2 = hash(todo)

        assert hash1 == hash2

    def test_different_ids_different_hashes(self) -> None:
        """Todos with different ids should have different hashes (not required but expected)."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=2, text="a")

        # Different ids should ideally have different hashes
        # (not strictly required but good for performance)
        assert hash(todo1) != hash(todo2)
