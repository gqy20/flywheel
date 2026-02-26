"""Tests for Todo.__eq__ and __hash__ methods (Issue #5986).

These tests verify that:
1. Todo objects with same data are equal
2. Todo objects can be used in sets
3. Todo hash is based on id for proper set/dict operations
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todo_equality_with_identical_data(self) -> None:
        """Two Todo objects with identical data should be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)

        assert todo1 == todo2

    def test_todo_equality_same_id_different_text(self) -> None:
        """Two Todo objects with same id but different text should NOT be equal.

        Per issue acceptance: equality compares id, text, and done.
        """
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy bread", done=False)

        assert todo1 != todo2

    def test_todo_equality_same_id_different_done(self) -> None:
        """Two Todo objects with same id but different done should NOT be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=True)

        assert todo1 != todo2

    def test_todo_equality_different_id_same_text(self) -> None:
        """Two Todo objects with different ids should NOT be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy milk", done=False)

        assert todo1 != todo2

    def test_todo_equality_with_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="buy milk", done=False)

        assert todo != "buy milk"
        assert todo != 1
        assert todo != {"id": 1, "text": "buy milk", "done": False}
        assert todo is not None

    def test_todo_equality_reflexive(self) -> None:
        """A Todo should be equal to itself."""
        todo = Todo(id=1, text="buy milk", done=False)

        assert todo == todo

    def test_todo_equality_symmetric(self) -> None:
        """Equality should be symmetric (a == b implies b == a)."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)

        assert todo1 == todo2
        assert todo2 == todo1

    def test_todo_equality_transitive(self) -> None:
        """Equality should be transitive (a == b and b == c implies a == c)."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)
        todo3 = Todo(id=1, text="buy milk", done=False)

        assert todo1 == todo2
        assert todo2 == todo3
        assert todo1 == todo3


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todo_hash_based_on_id(self) -> None:
        """Todo hash should be based on id (per issue acceptance criteria)."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy bread", done=True)

        # Same id should have same hash (per issue acceptance criteria)
        assert hash(todo1) == hash(todo2)

    def test_todo_hash_different_id(self) -> None:
        """Todo objects with different ids should have different hashes."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy milk", done=False)

        # Different ids should have different hashes
        assert hash(todo1) != hash(todo2)

    def test_todo_hash_stable(self) -> None:
        """Todo hash should be stable across multiple calls."""
        todo = Todo(id=1, text="buy milk", done=False)

        hash1 = hash(todo)
        hash2 = hash(todo)
        hash3 = hash(todo)

        assert hash1 == hash2 == hash3


class TestTodoInSet:
    """Tests for using Todo objects in sets."""

    def test_todo_can_be_added_to_set(self) -> None:
        """Todo objects should be addable to a set."""
        todo = Todo(id=1, text="buy milk", done=False)

        # Should not raise TypeError
        todo_set = {todo}
        assert todo in todo_set

    def test_todo_set_deduplication_by_id(self) -> None:
        """Set should deduplicate Todo objects by id (hash-based)."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy bread", done=True)  # Same id, different data

        todo_set = {todo1, todo2}

        # Since hash is based on id, both will have same hash
        # but they are not equal, so both will be in set
        # This is expected Python behavior
        assert len(todo_set) == 2

    def test_todo_set_with_different_ids(self) -> None:
        """Set should contain distinct Todo objects with different ids."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy bread", done=True)

        todo_set = {todo1, todo2}

        assert len(todo_set) == 2
        assert todo1 in todo_set
        assert todo2 in todo_set

    def test_todo_set_with_identical_todos(self) -> None:
        """Set should deduplicate identical Todo objects."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)

        todo_set = {todo1, todo2}

        # Equal objects should deduplicate
        assert len(todo_set) == 1


class TestTodoInDict:
    """Tests for using Todo objects as dict keys."""

    def test_todo_as_dict_key(self) -> None:
        """Todo objects should be usable as dict keys."""
        todo = Todo(id=1, text="buy milk", done=False)

        # Should not raise TypeError
        todo_dict = {todo: "value"}
        assert todo_dict[todo] == "value"

    def test_todo_dict_lookup_by_hash(self) -> None:
        """Dict lookup should work for Todo objects with same id."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy bread", done=True)

        todo_dict = {todo1: "first"}

        # Since they have same hash but are not equal, todo2 won't find todo1
        assert todo_dict.get(todo2) is None
