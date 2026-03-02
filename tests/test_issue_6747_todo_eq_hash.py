"""Tests for Todo __eq__ and __hash__ methods (Issue #6747).

These tests verify that:
1. Todo objects with the same id are equal (id-based equality)
2. Todo objects can be used in sets for deduplication
3. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todos_with_same_id_are_equal(self) -> None:
        """Todos with the same id should be equal regardless of other fields."""
        t1 = Todo(id=1, text="buy milk", done=False)
        t2 = Todo(id=1, text="different text", done=True)

        assert t1 == t2, "Todos with same id should be equal"

    def test_todos_with_different_id_are_not_equal(self) -> None:
        """Todos with different ids should not be equal."""
        t1 = Todo(id=1, text="same text", done=False)
        t2 = Todo(id=2, text="same text", done=False)

        assert t1 != t2, "Todos with different ids should not be equal"

    def test_todo_equals_itself(self) -> None:
        """A Todo should equal itself."""
        t = Todo(id=1, text="task")
        assert t == t

    def test_todo_not_equal_to_non_todo(self) -> None:
        """A Todo should not equal a non-Todo object."""
        t = Todo(id=1, text="task")
        assert t != "not a todo"
        assert t != 1
        assert t != {"id": 1, "text": "task"}
        assert t is not None


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todo_is_hashable(self) -> None:
        """Todo objects should be hashable."""
        t = Todo(id=1, text="task")
        # Should not raise TypeError
        hash(t)

    def test_todos_with_same_id_have_same_hash(self) -> None:
        """Todos with the same id should have the same hash."""
        t1 = Todo(id=1, text="text one")
        t2 = Todo(id=1, text="text two")

        assert hash(t1) == hash(t2)

    def test_todos_in_set(self) -> None:
        """Todo objects should work in a set for deduplication."""
        t1 = Todo(id=1, text="task one")
        t2 = Todo(id=1, text="task two")  # Same id as t1
        t3 = Todo(id=2, text="task three")

        todo_set = {t1, t2, t3}

        # Set should have 2 items (t1 and t2 are considered equal by id)
        assert len(todo_set) == 2, f"Expected 2 items in set, got {len(todo_set)}"

    def test_todos_as_dict_keys(self) -> None:
        """Todo objects should work as dictionary keys."""
        t1 = Todo(id=1, text="task one")
        t2 = Todo(id=1, text="task two")  # Same id as t1
        t3 = Todo(id=2, text="task three")

        todo_dict = {t1: "first", t2: "second", t3: "third"}

        # Dict should have 2 keys (t1 and t2 are considered equal by id)
        assert len(todo_dict) == 2, f"Expected 2 keys in dict, got {len(todo_dict)}"
        # t2 should overwrite t1's value since they have the same id
        assert todo_dict[t1] == "second"

    def test_hash_consistency(self) -> None:
        """Hash should be consistent across multiple calls."""
        t = Todo(id=42, text="consistent")
        h1 = hash(t)
        h2 = hash(t)
        assert h1 == h2
