"""Test for issue #6056: __eq__ and __hash__ methods for proper equality comparison."""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEqualityAndHash:
    """Tests for Todo equality comparison and hash functionality."""

    def test_equality_same_id_and_text(self) -> None:
        """Todo instances with same id and text should be equal."""
        todo1 = Todo(id=1, text="a", created_at="", updated_at="")
        todo2 = Todo(id=1, text="a", created_at="", updated_at="")
        assert todo1 == todo2

    def test_inequality_different_id(self) -> None:
        """Todo instances with different id should not be equal."""
        todo1 = Todo(id=1, text="a", created_at="", updated_at="")
        todo2 = Todo(id=2, text="a", created_at="", updated_at="")
        assert todo1 != todo2

    def test_equality_same_id_different_text(self) -> None:
        """Todo instances with same id should be equal for hash consistency."""
        todo1 = Todo(id=1, text="a", created_at="", updated_at="")
        todo2 = Todo(id=1, text="b", created_at="", updated_at="")
        # Equality is based on id only for hash consistency
        assert todo1 == todo2

    def test_hash_allows_set_usage(self) -> None:
        """Todo instances with same id should hash to same value for set deduplication."""
        todo1 = Todo(id=1, text="a", created_at="", updated_at="")
        todo2 = Todo(id=1, text="b", created_at="", updated_at="")
        # Both have same id, so they should be treated as same in a set
        todo_set = {todo1, todo2}
        assert len(todo_set) == 1

    def test_hash_different_ids_different_set_entries(self) -> None:
        """Todo instances with different ids should create separate set entries."""
        todo1 = Todo(id=1, text="a", created_at="", updated_at="")
        todo2 = Todo(id=2, text="a", created_at="", updated_at="")
        todo_set = {todo1, todo2}
        assert len(todo_set) == 2

    def test_hash_allows_dict_key_usage(self) -> None:
        """Todo instances should be usable as dict keys."""
        todo1 = Todo(id=1, text="a", created_at="", updated_at="")
        todo2 = Todo(id=1, text="b", created_at="", updated_at="")
        mapping = {todo1: "first"}
        # Same id should map to same key
        mapping[todo2] = "second"
        assert len(mapping) == 1
        assert mapping[todo1] == "second"
