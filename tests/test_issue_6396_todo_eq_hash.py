"""Tests for Todo __eq__ and __hash__ methods (Issue #6396).

These tests verify that Todo objects can be compared for equality
and used in sets/dicts for deduplication.
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_equal_todos_with_same_id_text_done(self) -> None:
        """Two Todo objects with same id, text, and done should be equal."""
        todo1 = Todo(id=1, text="a", done=False)
        todo2 = Todo(id=1, text="a", done=False)
        assert todo1 == todo2

    def test_unequal_todos_with_different_id(self) -> None:
        """Todo objects with different ids should not be equal."""
        todo1 = Todo(id=1, text="a", done=False)
        todo2 = Todo(id=2, text="a", done=False)
        assert todo1 != todo2

    def test_unequal_todos_with_different_text(self) -> None:
        """Todo objects with different text should not be equal."""
        todo1 = Todo(id=1, text="a", done=False)
        todo2 = Todo(id=1, text="b", done=False)
        assert todo1 != todo2

    def test_unequal_todos_with_different_done(self) -> None:
        """Todo objects with different done status should not be equal."""
        todo1 = Todo(id=1, text="a", done=False)
        todo2 = Todo(id=1, text="a", done=True)
        assert todo1 != todo2

    def test_todo_not_equal_to_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="a")
        assert todo != "not a todo"
        assert todo != 1
        assert todo != {"id": 1, "text": "a"}

    def test_equal_todos_ignore_timestamps(self) -> None:
        """Equality should only consider id, text, done (not timestamps)."""
        todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
        todo2 = Todo(id=1, text="a", done=False, created_at="2024-12-31", updated_at="2024-12-31")
        assert todo1 == todo2


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_hash_based_on_id(self) -> None:
        """Hash should be based on id (unique identifier)."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="a")
        assert hash(todo1) == hash(todo2)

    def test_different_ids_have_different_hashes(self) -> None:
        """Different ids should generally produce different hashes."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=2, text="a")
        # Different ids should produce different hashes (with high probability)
        assert hash(todo1) != hash(todo2)

    def test_todo_can_be_used_in_set(self) -> None:
        """Todo objects with same id should deduplicate in a set."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="a")
        todo_set = {todo1, todo2}
        assert len(todo_set) == 1

    def test_different_todos_in_set(self) -> None:
        """Different Todo objects should both exist in a set."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=2, text="b")
        todo_set = {todo1, todo2}
        assert len(todo_set) == 2

    def test_todo_can_be_used_as_dict_key(self) -> None:
        """Todo objects can be used as dictionary keys."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="a")
        d = {todo1: "value1"}
        d[todo2] = "value2"
        # Should have only one key since both todos are equal
        assert len(d) == 1
        assert d[todo1] == "value2"
