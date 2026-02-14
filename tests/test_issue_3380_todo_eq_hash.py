"""Tests for Todo __eq__ and __hash__ methods (issue #3380).

Acceptance criteria:
- Two Todos with the same id are considered equal
- Todos can be added to a set and deduplicated correctly
- Todos can be used as dict keys
- Does not affect existing dataclass behavior
"""

from flywheel.todo import Todo


class TestTodoEquality:
    """Test Todo equality comparison based on id."""

    def test_todos_with_same_id_are_equal(self):
        """Two Todos with the same id should be equal, even with different text."""
        todo1 = Todo(id=1, text="First todo")
        todo2 = Todo(id=1, text="Second todo")
        assert todo1 == todo2

    def test_todos_with_different_id_are_not_equal(self):
        """Two Todos with different ids should not be equal."""
        todo1 = Todo(id=1, text="Same text")
        todo2 = Todo(id=2, text="Same text")
        assert todo1 != todo2

    def test_todo_equal_to_itself(self):
        """A Todo should be equal to itself."""
        todo = Todo(id=1, text="Test")
        assert todo == todo

    def test_todo_not_equal_to_non_todo(self):
        """A Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="Test")
        assert todo != 1
        assert todo != "1"
        assert todo != {"id": 1, "text": "Test"}

    def test_equality_ignores_done_status(self):
        """Equality should ignore the done field."""
        todo1 = Todo(id=1, text="Test", done=False)
        todo2 = Todo(id=1, text="Test", done=True)
        assert todo1 == todo2

    def test_equality_ignores_timestamps(self):
        """Equality should ignore created_at and updated_at fields."""
        todo1 = Todo(
            id=1, text="Test", created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z"
        )
        todo2 = Todo(
            id=1, text="Test", created_at="2024-12-31T23:59:59Z", updated_at="2024-12-31T23:59:59Z"
        )
        assert todo1 == todo2


class TestTodoHash:
    """Test Todo hashing for use in sets and dict keys."""

    def test_todo_is_hashable(self):
        """Todo should be hashable."""
        todo = Todo(id=1, text="Test")
        hash(todo)  # Should not raise TypeError

    def test_todos_with_same_id_have_same_hash(self):
        """Two Todos with the same id should have the same hash."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=1, text="Second")
        assert hash(todo1) == hash(todo2)

    def test_todos_in_set_deduplicate_by_id(self):
        """Adding Todos with the same id to a set should deduplicate."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=1, text="Second")
        todo3 = Todo(id=2, text="Third")
        todo_set = {todo1, todo2, todo3}
        assert len(todo_set) == 2

    def test_todo_can_be_used_as_dict_key(self):
        """Todo can be used as a dictionary key."""
        todo1 = Todo(id=1, text="First")
        todo2 = Todo(id=1, text="Second")
        mapping = {todo1: "value1"}
        # Since they're equal, todo2 should access the same slot
        assert mapping[todo2] == "value1"

    def test_hash_consistency_across_objects(self):
        """Hash should be consistent for the same id across different objects."""
        hashes = set()
        for i in range(10):
            todo = Todo(id=42, text=f"Text {i}")
            hashes.add(hash(todo))
        assert len(hashes) == 1
