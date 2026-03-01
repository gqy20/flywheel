"""Tests for Todo.__eq__ and __hash__ methods (Issue #6606).

These tests verify that:
1. Todo objects with the same id are equal regardless of other fields
2. Todo objects with different ids are not equal
3. Todo objects can be hashed and used in sets/dicts
4. Set deduplication works based on id
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_same_id_different_text_are_equal(self) -> None:
        """Todos with same id should be equal regardless of text."""
        todo1 = Todo(id=1, text="buy milk")
        todo2 = Todo(id=1, text="buy bread")

        assert todo1 == todo2

    def test_same_id_different_done_are_equal(self) -> None:
        """Todos with same id should be equal regardless of done status."""
        todo1 = Todo(id=1, text="task", done=False)
        todo2 = Todo(id=1, text="task", done=True)

        assert todo1 == todo2

    def test_different_id_same_text_are_not_equal(self) -> None:
        """Todos with different ids should not be equal even with same text."""
        todo1 = Todo(id=1, text="task")
        todo2 = Todo(id=2, text="task")

        assert todo1 != todo2

    def test_different_id_different_text_are_not_equal(self) -> None:
        """Todos with different ids should not be equal."""
        todo1 = Todo(id=1, text="task a")
        todo2 = Todo(id=2, text="task b")

        assert todo1 != todo2

    def test_todo_not_equal_to_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="task")

        assert todo != "task"
        assert todo != 1
        assert todo != {"id": 1, "text": "task"}
        assert todo != None

    def test_todo_equal_to_itself(self) -> None:
        """Todo should be equal to itself (reflexivity)."""
        todo = Todo(id=1, text="task")

        assert todo == todo


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todo_is_hashable(self) -> None:
        """Todo objects should be hashable."""
        todo = Todo(id=1, text="task")

        # Should not raise TypeError
        hash(todo)

    def test_same_id_same_hash(self) -> None:
        """Todos with same id should have same hash."""
        todo1 = Todo(id=1, text="buy milk")
        todo2 = Todo(id=1, text="buy bread")

        assert hash(todo1) == hash(todo2)

    def test_different_id_different_hash(self) -> None:
        """Todos with different ids should (likely) have different hashes."""
        todo1 = Todo(id=1, text="task")
        todo2 = Todo(id=2, text="task")

        # While hash collisions are possible, for sequential ints this should hold
        assert hash(todo1) != hash(todo2)

    def test_hash_stable_after_done_change(self) -> None:
        """Hash should remain stable when done status changes."""
        todo = Todo(id=1, text="task", done=False)
        original_hash = hash(todo)

        todo.mark_done()

        assert hash(todo) == original_hash


class TestTodoInSet:
    """Tests for using Todo objects in sets."""

    def test_todo_can_be_added_to_set(self) -> None:
        """Todo objects should be addable to a set."""
        todo = Todo(id=1, text="task")

        # Should not raise TypeError
        todo_set = {todo}
        assert len(todo_set) == 1

    def test_set_deduplicates_by_id(self) -> None:
        """Set should deduplicate Todo objects by id."""
        todo1 = Todo(id=1, text="buy milk")
        todo2 = Todo(id=1, text="buy bread")  # Same id, different text
        todo3 = Todo(id=2, text="buy eggs")

        todo_set = {todo1, todo2, todo3}

        # Should only have 2 unique todos (by id)
        assert len(todo_set) == 2

    def test_membership_test_by_id(self) -> None:
        """Set membership should work based on id."""
        todo1 = Todo(id=1, text="buy milk")
        todo_set = {todo1}

        # Different Todo instance with same id should be "in" the set
        todo2 = Todo(id=1, text="buy bread")
        assert todo2 in todo_set

        # Different id should not be in set
        todo3 = Todo(id=2, text="buy milk")
        assert todo3 not in todo_set


class TestTodoAsDictKey:
    """Tests for using Todo objects as dictionary keys."""

    def test_todo_can_be_dict_key(self) -> None:
        """Todo objects should be usable as dictionary keys."""
        todo = Todo(id=1, text="task")

        # Should not raise TypeError
        todo_dict = {todo: "value"}
        assert todo_dict[todo] == "value"

    def test_dict_key_lookup_by_id(self) -> None:
        """Dict lookup should work based on id equality."""
        todo1 = Todo(id=1, text="buy milk")
        todo_dict = {todo1: "original"}

        # Different Todo instance with same id should find the value
        todo2 = Todo(id=1, text="buy bread")
        assert todo_dict[todo2] == "original"
