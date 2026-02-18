"""Test Todo hashability for set/dict usage.

Issue: #4176
Enhancement: Add __hash__ method to make Todo hashable for set/dict usage.

Acceptance criteria:
- hash(Todo(1, 'test')) does not raise TypeError
- Todo objects can be added to a set
- Same id produces same hash
"""

from flywheel.todo import Todo


class TestTodoHashable:
    """Tests for Todo hashability support."""

    def test_todo_is_hashable(self):
        """Test that hash() on a Todo object does not raise TypeError."""
        todo = Todo(id=1, text="test")
        # Should not raise TypeError
        hash_value = hash(todo)
        assert isinstance(hash_value, int)

    def test_same_id_produces_same_hash(self):
        """Test that Todo objects with same id have same hash."""
        todo1 = Todo(id=1, text="first")
        todo2 = Todo(id=1, text="second")
        assert hash(todo1) == hash(todo2)

    def test_different_id_produces_different_hash(self):
        """Test that Todo objects with different ids have different hashes."""
        todo1 = Todo(id=1, text="same text")
        todo2 = Todo(id=2, text="same text")
        assert hash(todo1) != hash(todo2)

    def test_todo_can_be_added_to_set(self):
        """Test that Todo objects can be added to a set."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=2, text="b")
        todo_set = {todo1, todo2}
        assert len(todo_set) == 2
        assert todo1 in todo_set
        assert todo2 in todo_set

    def test_set_deduplication_by_id(self):
        """Test that set deduplicates Todo objects by id."""
        # Two todos with same id should deduplicate in a set
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="a")
        todo_set = {todo1, todo2}
        assert len(todo_set) == 1

    def test_todo_can_be_dict_key(self):
        """Test that Todo objects can be used as dictionary keys."""
        todo = Todo(id=1, text="a")
        d = {todo: "value"}
        assert d[todo] == "value"

    def test_dict_lookup_by_hash_equivalent(self):
        """Test that dict lookup works with same-id Todo object."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")
        d = {todo1: "value"}
        # Same id means same hash, so lookup should work
        assert d[todo2] == "value"

    def test_hash_consistency_after_modification(self):
        """Test that hash remains consistent based on id even if other fields change.

        Note: This test documents that hash is based on id field.
        If the todo's text changes, hash should remain the same.
        """
        todo = Todo(id=1, text="original")
        original_hash = hash(todo)
        todo.rename("modified")
        # Hash should still be based on id, not text
        assert hash(todo) == original_hash
