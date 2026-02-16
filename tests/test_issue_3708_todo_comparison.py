"""Tests for Todo comparison and ordering capabilities (issue #3708)."""

import pytest

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for __eq__ comparison."""

    def test_todo_equality_same_id_and_text(self) -> None:
        """Two Todo objects with same id and text should be equal."""
        # Use fixed timestamps to avoid timing issues
        ts = "2024-01-01T00:00:00+00:00"
        todo1 = Todo(id=1, text="Buy milk", done=False, created_at=ts, updated_at=ts)
        todo2 = Todo(id=1, text="Buy milk", done=False, created_at=ts, updated_at=ts)
        assert todo1 == todo2

    def test_todo_inequality_different_id(self) -> None:
        """Two Todo objects with different ids should not be equal."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy milk")
        assert todo1 != todo2

    def test_todo_inequality_different_text(self) -> None:
        """Two Todo objects with different text should not be equal."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")
        assert todo1 != todo2

    def test_todo_not_equal_to_non_todo(self) -> None:
        """Todo should not equal non-Todo objects."""
        todo = Todo(id=1, text="Buy milk")
        assert todo != "Buy milk"
        assert todo != 1
        assert todo != {"id": 1, "text": "Buy milk"}


class TestTodoOrdering:
    """Tests for __lt__ comparison for sorting."""

    def test_todo_ordering_by_id(self) -> None:
        """Todo objects should be orderable by id."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=2, text="Second")
        assert todo1 < todo2
        assert todo2 > todo1

    def test_todo_sorting_by_id(self) -> None:
        """A list of Todo objects should be sortable by id."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=2, text="Second")
        todo3 = Todo(id=3, text="Third")
        unsorted_list = [todo3, todo1, todo2]
        sorted_list = sorted(unsorted_list)
        assert sorted_list == [todo1, todo2, todo3]

    def test_todo_ordering_with_same_id_different_text(self) -> None:
        """When id is same, ordering should use text as tiebreaker."""
        todo_a = Todo(id=1, text="Apple")
        todo_b = Todo(id=1, text="Banana")
        assert todo_a < todo_b  # "Apple" < "Banana"

    def test_todo_less_than_raises_type_error_for_non_todo(self) -> None:
        """Comparing Todo with non-Todo should raise TypeError."""
        todo = Todo(id=1, text="Test")
        with pytest.raises(TypeError):
            _ = todo < 1


class TestTodoHash:
    """Tests for __hash__ for set operations."""

    def test_todo_hash_consistent(self) -> None:
        """Same Todo should produce consistent hash."""
        todo = Todo(id=1, text="Buy milk")
        hash1 = hash(todo)
        hash2 = hash(todo)
        assert hash1 == hash2

    def test_todo_hash_same_content_equal(self) -> None:
        """Two equal Todo objects should have same hash."""
        todo1 = Todo(id=1, text="Buy milk", done=False)
        todo2 = Todo(id=1, text="Buy milk", done=False)
        assert hash(todo1) == hash(todo2)

    def test_todo_usable_in_set(self) -> None:
        """Todo objects should be usable in sets."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy bread")
        todo1_copy = Todo(id=1, text="Buy milk")  # Same as todo1
        todo_set = {todo1, todo2, todo1_copy}
        # Equal todos should deduplicate
        assert len(todo_set) == 2

    def test_todo_usable_as_dict_key(self) -> None:
        """Todo objects should be usable as dictionary keys."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy bread")
        todo_dict = {todo1: "A", todo2: "B"}
        # Same content todo should map to same key
        todo1_copy = Todo(id=1, text="Buy milk")
        assert todo_dict[todo1_copy] == "A"
