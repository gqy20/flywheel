"""Tests for Todo __eq__ and __hash__ methods (Issue #4287)."""

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo equality comparison."""

    def test_todos_with_same_id_are_equal(self) -> None:
        """Todo(1, 'a') == Todo(1, 'b') should return True (same id means same task)."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")
        assert todo1 == todo2

    def test_todos_with_different_id_are_not_equal(self) -> None:
        """Todo(1, 'a') != Todo(2, 'a') should return True."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=2, text="a")
        assert todo1 != todo2

    def test_equality_ignores_done_status(self) -> None:
        """Todos with same id but different done status should be equal."""
        todo1 = Todo(id=1, text="task", done=False)
        todo2 = Todo(id=1, text="task", done=True)
        assert todo1 == todo2

    def test_equality_ignores_timestamps(self) -> None:
        """Todos with same id but different timestamps should be equal."""
        todo1 = Todo(id=1, text="task")
        todo1.created_at = "2024-01-01T00:00:00+00:00"
        todo1.updated_at = "2024-01-01T00:00:00+00:00"

        todo2 = Todo(id=1, text="task")
        todo2.created_at = "2024-12-31T23:59:59+00:00"
        todo2.updated_at = "2024-12-31T23:59:59+00:00"

        assert todo1 == todo2


class TestTodoHash:
    """Tests for Todo hash support for set operations."""

    def test_todos_are_hashable(self) -> None:
        """Todo objects should be hashable."""
        todo = Todo(id=1, text="task")
        # Should not raise TypeError
        hash(todo)

    def test_todos_with_same_id_have_same_hash(self) -> None:
        """Todos with same id should have same hash."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")
        assert hash(todo1) == hash(todo2)

    def test_todos_with_different_id_have_different_hash(self) -> None:
        """Todos with different id should (likely) have different hash."""
        todo1 = Todo(id=1, text="task")
        todo2 = Todo(id=2, text="task")
        # Hash collision is possible but unlikely for consecutive integers
        assert hash(todo1) != hash(todo2)

    def test_set_deduplication(self) -> None:
        """set([todo1, todo2, todo1]) should have length 2."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=2, text="b")
        todo3 = Todo(id=1, text="c")  # Same id as todo1

        result = {todo1, todo2, todo3}
        assert len(result) == 2

    def test_set_contains_todo_by_id(self) -> None:
        """Should be able to check if a Todo is in a set by id."""
        todo1 = Todo(id=1, text="original")
        todo_set = {todo1}

        # A different Todo with same id should be "in" the set
        todo2 = Todo(id=1, text="different text")
        assert todo2 in todo_set

        # A Todo with different id should not be "in" the set
        todo3 = Todo(id=2, text="different id")
        assert todo3 not in todo_set
