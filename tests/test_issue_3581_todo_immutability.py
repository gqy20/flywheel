"""Tests for Todo immutability/copy support (Issue #3581).

Tests for __eq__, __hash__, and copy method.
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Test Todo.__eq__ for value-based equality."""

    def test_todos_with_same_id_text_done_are_equal(self) -> None:
        """Todo(1, 'a') == Todo(1, 'a') should return True."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = Todo(id=1, text="a", done=False)
        assert t1 == t2

    def test_todos_with_same_id_text_done_but_different_timestamps_are_equal(
        self,
    ) -> None:
        """Equality should ignore timestamps (created_at, updated_at)."""
        t1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
        t2 = Todo(id=1, text="a", done=False, created_at="2024-12-31", updated_at="2024-12-31")
        assert t1 == t2

    def test_todos_with_different_id_are_not_equal(self) -> None:
        """Todos with different ids should not be equal."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = Todo(id=2, text="a", done=False)
        assert t1 != t2

    def test_todos_with_different_text_are_not_equal(self) -> None:
        """Todos with different text should not be equal."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = Todo(id=1, text="b", done=False)
        assert t1 != t2

    def test_todos_with_different_done_are_not_equal(self) -> None:
        """Todos with different done status should not be equal."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = Todo(id=1, text="a", done=True)
        assert t1 != t2

    def test_todo_not_equal_to_non_todo(self) -> None:
        """Todo should not be equal to non-Todo objects."""
        t1 = Todo(id=1, text="a", done=False)
        assert t1 != "not a todo"
        assert t1 != 1
        assert t1 != {"id": 1, "text": "a", "done": False}


class TestTodoHash:
    """Test Todo.__hash__ for use in sets and dicts."""

    def test_hash_does_not_raise(self) -> None:
        """hash(Todo(1, 'a')) should not raise an exception."""
        t = Todo(id=1, text="a", done=False)
        # This should not raise
        hash(t)

    def test_same_todos_have_same_hash(self) -> None:
        """Equal Todos should have the same hash."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = Todo(id=1, text="a", done=False)
        assert hash(t1) == hash(t2)

    def test_todos_can_be_used_in_set(self) -> None:
        """Todos should be usable in a set for deduplication."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = Todo(id=1, text="a", done=False)
        t3 = Todo(id=2, text="b", done=False)

        todo_set = {t1, t2, t3}
        # Equal todos should be deduplicated
        assert len(todo_set) == 2

    def test_todos_can_be_used_as_dict_keys(self) -> None:
        """Todos should be usable as dictionary keys."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = Todo(id=1, text="a", done=False)

        d = {t1: "value1"}
        # Equal todo should access the same key
        assert d[t2] == "value1"


class TestTodoCopy:
    """Test Todo.copy method for creating derived objects."""

    def test_copy_returns_new_instance(self) -> None:
        """copy() should return a new Todo instance."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = t1.copy()
        assert t2 is not t1
        assert isinstance(t2, Todo)

    def test_copy_preserves_all_fields(self) -> None:
        """copy() without arguments should preserve all fields."""
        t1 = Todo(id=1, text="a", done=True, created_at="2024-01-01", updated_at="2024-01-02")
        t2 = t1.copy()
        assert t2.id == t1.id
        assert t2.text == t1.text
        assert t2.done == t1.done
        assert t2.created_at == t1.created_at
        assert t2.updated_at == t1.updated_at

    def test_copy_with_text_override(self) -> None:
        """copy(text='new') should return a new instance with updated text."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = t1.copy(text="b")
        assert t2.text == "b"
        assert t1.text == "a"  # Original unchanged

    def test_copy_with_done_override(self) -> None:
        """copy(done=True) should return a new instance with updated done."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = t1.copy(done=True)
        assert t2.done is True
        assert t1.done is False  # Original unchanged

    def test_copy_with_id_override(self) -> None:
        """copy(id=2) should return a new instance with updated id."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = t1.copy(id=2)
        assert t2.id == 2
        assert t1.id == 1  # Original unchanged

    def test_copy_with_multiple_overrides(self) -> None:
        """copy() should accept multiple field overrides."""
        t1 = Todo(id=1, text="a", done=False)
        t2 = t1.copy(id=2, text="b", done=True)
        assert t2.id == 2
        assert t2.text == "b"
        assert t2.done is True
        # Original unchanged
        assert t1.id == 1
        assert t1.text == "a"
        assert t1.done is False
