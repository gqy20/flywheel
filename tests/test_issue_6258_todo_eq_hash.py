"""Tests for Todo __eq__ and __hash__ methods (issue #6258)."""

from flywheel.todo import Todo


class TestTodoEquality:
    """Test cases for Todo.__eq__ method."""

    def test_todos_with_same_id_are_equal(self) -> None:
        """Todo objects with the same id should be equal regardless of other fields."""
        todo1 = Todo(id=1, text="Buy milk", done=False)
        todo2 = Todo(id=1, text="Buy bread", done=True)

        assert todo1 == todo2

    def test_todos_with_different_ids_are_not_equal(self) -> None:
        """Todo objects with different ids should not be equal."""
        todo1 = Todo(id=1, text="Buy milk", done=False)
        todo2 = Todo(id=2, text="Buy milk", done=False)

        assert todo1 != todo2

    def test_todo_not_equal_to_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="Buy milk")

        assert todo != "not a todo"
        assert todo != 1
        assert todo != {"id": 1, "text": "Buy milk"}
        assert todo is not None

    def test_todo_equal_to_itself(self) -> None:
        """Todo should be equal to itself."""
        todo = Todo(id=1, text="Buy milk")

        assert todo == todo


class TestTodoHash:
    """Test cases for Todo.__hash__ method."""

    def test_hash_works_without_type_error(self) -> None:
        """hash() should work on Todo without raising TypeError."""
        todo = Todo(id=1, text="Buy milk")

        # Should not raise TypeError
        hash(todo)

    def test_todos_with_same_id_have_same_hash(self) -> None:
        """Todo objects with the same id should have the same hash."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")

        assert hash(todo1) == hash(todo2)

    def test_todos_with_different_ids_have_different_hashes(self) -> None:
        """Todo objects with different ids typically have different hashes."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy milk")

        # Not guaranteed, but very likely for different ids
        assert hash(todo1) != hash(todo2)


class TestTodoSetOperations:
    """Test cases for using Todo in sets."""

    def test_set_deduplication_by_id(self) -> None:
        """Set should deduplicate Todo objects by id."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")  # Same id, different text
        todo3 = Todo(id=2, text="Buy eggs")

        todo_set = {todo1, todo2, todo3}

        assert len(todo_set) == 2

    def test_set_membership_by_id(self) -> None:
        """Set membership should work based on id."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")  # Same id, different text
        todo_set = {todo1}

        assert todo2 in todo_set

    def test_dict_key_by_todo(self) -> None:
        """Todo should work as a dictionary key based on id."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")  # Same id, different text

        d = {todo1: "value1"}

        # Should find the value using a Todo with the same id
        assert d[todo2] == "value1"
