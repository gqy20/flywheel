"""Tests for Todo __eq__ and __hash__ methods (issue #4537)."""

from flywheel.todo import Todo


class TestTodoEq:
    """Test cases for Todo.__eq__ method."""

    def test_todo_eq_same_id_and_text_returns_true(self) -> None:
        """Two Todo objects with same id and text should be equal."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy milk")
        assert todo1 == todo2

    def test_todo_eq_different_id_returns_false(self) -> None:
        """Two Todo objects with different id should not be equal."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy milk")
        assert todo1 != todo2

    def test_todo_eq_different_text_returns_false(self) -> None:
        """Two Todo objects with different text should not be equal."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")
        assert todo1 != todo2

    def test_todo_eq_different_done_returns_false(self) -> None:
        """Two Todo objects with different done status should not be equal."""
        todo1 = Todo(id=1, text="Buy milk", done=False)
        todo2 = Todo(id=1, text="Buy milk", done=True)
        assert todo1 != todo2

    def test_todo_eq_non_todo_returns_not_implemented(self) -> None:
        """Comparing Todo with non-Todo should return NotImplemented."""
        todo = Todo(id=1, text="Buy milk")
        # The comparison should return NotImplemented, which Python converts to False
        assert todo != "not a todo"
        assert todo != 1
        assert todo != {"id": 1, "text": "Buy milk"}

    def test_todo_eq_reflexive(self) -> None:
        """A Todo object should equal itself."""
        todo = Todo(id=1, text="Buy milk")
        assert todo == todo

    def test_todo_eq_symmetric(self) -> None:
        """Equality should be symmetric (a == b implies b == a)."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy milk")
        assert todo1 == todo2
        assert todo2 == todo1

    def test_todo_eq_transitive(self) -> None:
        """Equality should be transitive (a == b and b == c implies a == c)."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy milk")
        todo3 = Todo(id=1, text="Buy milk")
        assert todo1 == todo2
        assert todo2 == todo3
        assert todo1 == todo3


class TestTodoHash:
    """Test cases for Todo.__hash__ method."""

    def test_todo_hash_consistent_for_same_id(self) -> None:
        """Two Todo objects with same id should have same hash."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")
        # Hash is based on id, so same id = same hash
        assert hash(todo1) == hash(todo2)

    def test_todo_hash_different_for_different_id(self) -> None:
        """Two Todo objects with different id should have different hash."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy milk")
        # Different ids should typically produce different hashes (not guaranteed)
        # but at least they should not be equal
        assert hash(todo1) != hash(todo2)

    def test_todo_hash_stable(self) -> None:
        """Hash should be stable across multiple calls."""
        todo = Todo(id=1, text="Buy milk")
        hash1 = hash(todo)
        hash2 = hash(todo)
        assert hash1 == hash2


class TestTodoSetOperations:
    """Test cases for using Todo in sets and deduplication."""

    def test_todo_can_be_added_to_set(self) -> None:
        """Todo objects should be addable to a set."""
        todo = Todo(id=1, text="Buy milk")
        todo_set = {todo}
        assert todo in todo_set

    def test_todo_set_deduplication_by_id(self) -> None:
        """Set should deduplicate Todo objects by id (via hash)."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")
        todo_set = {todo1, todo2}
        # Since hash is based on id, both have same hash
        # but they are not equal (different text), so set keeps one
        # Actually, since __hash__ is based on id but __eq__ compares id, text, done,
        # two todos with same id but different text will have same hash but be unequal
        # In Python, hash collision is allowed but __eq__ is used to differentiate
        # So the set will have 2 elements since they're not equal
        assert len(todo_set) == 2  # Not equal, so both kept

    def test_todo_set_deduplication_equal_objects(self) -> None:
        """Set should deduplicate truly equal Todo objects."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy milk")
        todo_set = {todo1, todo2}
        # Equal objects should be deduplicated
        assert len(todo_set) == 1

    def test_todo_set_different_ids(self) -> None:
        """Set should keep Todo objects with different ids."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy milk")
        todo_set = {todo1, todo2}
        assert len(todo_set) == 2

    def test_todo_in_operator(self) -> None:
        """The 'in' operator should work with Todo objects in list/set."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy milk")
        todo_list = [todo1]
        assert todo2 in todo_list  # Uses __eq__


class TestTodoDictKey:
    """Test cases for using Todo as dict keys."""

    def test_todo_can_be_dict_key(self) -> None:
        """Todo objects should be usable as dict keys."""
        todo = Todo(id=1, text="Buy milk")
        todo_dict = {todo: "value"}
        assert todo_dict[todo] == "value"

    def test_todo_dict_lookup_by_equal_object(self) -> None:
        """Dict lookup should work with equal Todo objects."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy milk")
        todo_dict = {todo1: "value"}
        assert todo_dict[todo2] == "value"  # Same hash and equal
