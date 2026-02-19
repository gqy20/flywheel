"""Test cases for Todo __eq__ and __hash__ methods (issue #4468)."""

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todos_with_same_id_are_equal(self) -> None:
        """Todos with same id should be equal regardless of other fields."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=1, text="Walk the dog", done=True)
        assert todo1 == todo2

    def test_todos_with_different_id_are_not_equal(self) -> None:
        """Todos with different id should not be equal."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=2, text="Buy groceries", done=False)
        assert todo1 != todo2

    def test_todo_not_equal_to_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="Buy groceries", done=False)
        assert todo != 1
        assert todo != "Todo"
        assert todo != {"id": 1, "text": "Buy groceries"}


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_hash_is_stable(self) -> None:
        """Hash should be stable across multiple calls."""
        todo = Todo(id=1, text="Buy groceries", done=False)
        assert hash(todo) == hash(todo)

    def test_todos_with_same_id_have_same_hash(self) -> None:
        """Todos with same id should have same hash."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=1, text="Walk the dog", done=True)
        assert hash(todo1) == hash(todo2)

    def test_todos_with_different_id_have_different_hash(self) -> None:
        """Todos with different id should have different hash."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=2, text="Buy groceries", done=False)
        assert hash(todo1) != hash(todo2)


class TestTodoSetMembership:
    """Tests for using Todo in sets."""

    def test_todo_can_be_added_to_set(self) -> None:
        """Todo objects should be usable in sets."""
        todo = Todo(id=1, text="Buy groceries", done=False)
        todo_set = {todo}
        assert todo in todo_set

    def test_set_deduplicates_by_id(self) -> None:
        """Set should deduplicate Todo objects with same id."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=1, text="Walk the dog", done=True)
        todo_set = {todo1, todo2}
        assert len(todo_set) == 1


class TestTodoDictKeys:
    """Tests for using Todo as dict keys."""

    def test_todo_can_be_dict_key(self) -> None:
        """Todo objects should be usable as dict keys."""
        todo = Todo(id=1, text="Buy groceries", done=False)
        mapping = {todo: "value"}
        assert mapping[todo] == "value"

    def test_dict_key_lookup_by_equal_todo(self) -> None:
        """Dict should find value using different Todo with same id."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=1, text="Walk the dog", done=True)
        mapping = {todo1: "value"}
        assert mapping[todo2] == "value"
