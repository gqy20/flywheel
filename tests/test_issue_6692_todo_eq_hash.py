"""Tests for Todo.__eq__ and __hash__ methods (Issue #6692).

These tests verify that:
1. Todo objects with same id/text/done are equal
2. Todo objects with different id are not equal
3. Todo objects can be used in sets and dicts
4. Timestamps do not affect equality
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEq:
    """Tests for Todo.__eq__ method."""

    def test_eq_same_id_text_done(self) -> None:
        """Todos with same id, text, and done should be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)
        assert todo1 == todo2

    def test_eq_different_id(self) -> None:
        """Todos with different id should not be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy milk", done=False)
        assert todo1 != todo2

    def test_eq_different_text(self) -> None:
        """Todos with different text should not be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy bread", done=False)
        assert todo1 != todo2

    def test_eq_different_done(self) -> None:
        """Todos with different done status should not be equal."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=True)
        assert todo1 != todo2

    def test_eq_ignores_timestamps(self) -> None:
        """Equality should ignore created_at and updated_at."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)
        # Force different timestamps
        todo1.created_at = "2024-01-01T00:00:00+00:00"
        todo1.updated_at = "2024-01-01T00:00:00+00:00"
        todo2.created_at = "2024-12-31T23:59:59+00:00"
        todo2.updated_at = "2024-12-31T23:59:59+00:00"
        assert todo1 == todo2


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_hash_allows_set_usage(self) -> None:
        """Todo objects should be usable in a set."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy bread", done=False)
        todo_set = {todo1, todo2}
        assert len(todo_set) == 2
        assert todo1 in todo_set
        assert todo2 in todo_set

    def test_hash_deduplication(self) -> None:
        """Set should deduplicate Todos with same id/text/done."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)
        todo_set = {todo1, todo2}
        assert len(todo_set) == 1

    def test_hash_different_id_different_hash(self) -> None:
        """Todos with different id should have different hashes."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy milk", done=False)
        # While hash collisions are possible, for small integers they should differ
        assert hash(todo1) != hash(todo2)

    def test_hash_same_id_same_hash(self) -> None:
        """Todos with same id should have same hash."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=1, text="buy milk", done=False)
        assert hash(todo1) == hash(todo2)

    def test_hash_allows_dict_key_usage(self) -> None:
        """Todo objects should be usable as dict keys."""
        todo1 = Todo(id=1, text="buy milk", done=False)
        todo2 = Todo(id=2, text="buy bread", done=False)
        todo_dict = {todo1: "first", todo2: "second"}
        assert todo_dict[todo1] == "first"
        assert todo_dict[todo2] == "second"
