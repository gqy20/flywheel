"""Tests for Todo immutability/copy support (Issue #3581).

These tests verify that:
1. Todo objects support equality comparison via __eq__
2. Todo objects are hashable via __hash__
3. Todo objects support copy method for creating derived instances
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todo_equality_same_id_text_done(self) -> None:
        """Todo(1, 'a') == Todo(1, 'a') should return True."""
        todo1 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        todo2 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        assert todo1 == todo2

    def test_todo_equality_different_id(self) -> None:
        """Todos with different ids should not be equal."""
        todo1 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        todo2 = Todo(id=2, text="a", done=False, created_at="", updated_at="")
        assert todo1 != todo2

    def test_todo_equality_different_text(self) -> None:
        """Todos with different text should not be equal."""
        todo1 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        todo2 = Todo(id=1, text="b", done=False, created_at="", updated_at="")
        assert todo1 != todo2

    def test_todo_equality_different_done(self) -> None:
        """Todos with different done status should not be equal."""
        todo1 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        todo2 = Todo(id=1, text="a", done=True, created_at="", updated_at="")
        assert todo1 != todo2

    def test_todo_equality_with_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        todo = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        assert todo != "not a todo"
        assert todo != 1
        assert todo is not None
        assert todo != {"id": 1, "text": "a", "done": False}


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todo_hash_is_consistent(self) -> None:
        """hash(Todo) should be consistent for equal todos."""
        todo1 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        todo2 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        assert hash(todo1) == hash(todo2)

    def test_todo_hash_does_not_raise(self) -> None:
        """hash(Todo) should not raise an exception."""
        todo = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        # This should not raise
        hash_value = hash(todo)
        assert isinstance(hash_value, int)

    def test_todo_can_be_used_in_set(self) -> None:
        """Todo objects should be usable in a set for deduplication."""
        todo1 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        todo2 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        todo3 = Todo(id=2, text="b", done=False, created_at="", updated_at="")

        todo_set = {todo1, todo2, todo3}
        # Equal todos should deduplicate
        assert len(todo_set) == 2

    def test_todo_can_be_used_as_dict_key(self) -> None:
        """Todo objects should be usable as dict keys."""
        todo1 = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        todo2 = Todo(id=1, text="a", done=False, created_at="", updated_at="")

        d = {todo1: "first"}
        # Equal todo should map to same key
        assert d[todo2] == "first"


class TestTodoCopy:
    """Tests for Todo.copy method."""

    def test_todo_copy_text(self) -> None:
        """todo.copy(text='new') should return a new instance with updated text."""
        original = Todo(id=1, text="original", done=False, created_at="", updated_at="")
        copied = original.copy(text="new")

        assert copied.text == "new"
        assert original.text == "original"  # Original unchanged

    def test_todo_copy_done(self) -> None:
        """todo.copy(done=True) should return a new instance with done=True."""
        original = Todo(id=1, text="task", done=False, created_at="", updated_at="")
        copied = original.copy(done=True)

        assert copied.done is True
        assert original.done is False  # Original unchanged

    def test_todo_copy_multiple_fields(self) -> None:
        """todo.copy() should handle multiple field updates."""
        original = Todo(id=1, text="a", done=False, created_at="", updated_at="")
        copied = original.copy(text="b", done=True)

        assert copied.text == "b"
        assert copied.done is True
        assert copied.id == 1  # id should be preserved

    def test_todo_copy_no_args_returns_equal_instance(self) -> None:
        """todo.copy() with no args should return an equal instance."""
        original = Todo(id=1, text="task", done=False, created_at="", updated_at="")
        copied = original.copy()

        assert copied == original
        assert copied is not original  # Different objects

    def test_todo_copy_preserves_timestamps(self) -> None:
        """todo.copy() should preserve timestamps unless explicitly overridden."""
        original = Todo(
            id=1,
            text="task",
            done=False,
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-02T00:00:00+00:00",
        )
        copied = original.copy(text="new task")

        assert copied.created_at == "2024-01-01T00:00:00+00:00"
        assert copied.updated_at == "2024-01-02T00:00:00+00:00"
