"""Regression test for issue #3045: Todo __eq__ and __hash__ methods.

This test verifies that Todo objects:
1. Compare equal based only on id (not all fields)
2. Can be used in sets for deduplication
3. Can be used as dictionary keys
"""

from flywheel.todo import Todo


class TestTodoEquality:
    """Test Todo __eq__ method based on id only."""

    def test_same_id_equal_even_with_different_text(self):
        """Todos with same id should be equal regardless of text."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=1, text="Buy milk", done=True)
        assert todo1 == todo2

    def test_same_id_equal_even_with_different_done(self):
        """Todos with same id should be equal regardless of done status."""
        todo1 = Todo(id=1, text="Task", done=False)
        todo2 = Todo(id=1, text="Task", done=True)
        assert todo1 == todo2

    def test_different_id_not_equal(self):
        """Todos with different ids should not be equal."""
        todo1 = Todo(id=1, text="Same text", done=True)
        todo2 = Todo(id=2, text="Same text", done=True)
        assert todo1 != todo2

    def test_not_equal_to_non_todo(self):
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="Task")
        assert todo != 1
        assert todo != "Task"
        assert todo != {"id": 1, "text": "Task"}


class TestTodoHash:
    """Test Todo __hash__ method for set/dict operations."""

    def test_hash_does_not_raise(self):
        """hash(Todo) should not raise TypeError."""
        todo = Todo(id=1, text="Task")
        # This should not raise
        hash(todo)

    def test_same_id_same_hash(self):
        """Todos with same id should have same hash."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=1, text="Buy milk", done=True)
        assert hash(todo1) == hash(todo2)

    def test_can_add_to_set(self):
        """Todo objects should be addable to a set."""
        todo1 = Todo(id=1, text="Task 1")
        todo2 = Todo(id=2, text="Task 2")
        todo_set = {todo1, todo2}
        assert len(todo_set) == 2
        assert todo1 in todo_set
        assert todo2 in todo_set

    def test_set_deduplication_by_id(self):
        """Set should deduplicate Todos by id."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=1, text="Buy milk", done=True)  # Same id, different content
        todo_set = {todo1, todo2}
        # Both have id=1, so set should have only 1 element
        assert len(todo_set) == 1

    def test_can_use_as_dict_key(self):
        """Todo objects should be usable as dictionary keys."""
        todo1 = Todo(id=1, text="Task 1")
        todo2 = Todo(id=2, text="Task 2")
        mapping = {todo1: "first", todo2: "second"}
        assert mapping[todo1] == "first"
        assert mapping[todo2] == "second"

    def test_dict_key_lookup_by_equal_todo(self):
        """Dict should find value using a different but equal Todo instance."""
        todo1 = Todo(id=1, text="Original text")
        mapping = {todo1: "value"}
        # Create a new Todo with same id but different content
        todo2 = Todo(id=1, text="Different text")
        # Since __eq__ compares by id, todo2 should find the key
        assert mapping[todo2] == "value"
