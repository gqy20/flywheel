"""Tests for Todo.__eq__ method (issue #4440).

These tests verify id-based equality comparison for Todo objects.
"""

from flywheel.todo import Todo


class TestTodoEq:
    """Test suite for Todo.__eq__ method."""

    def test_todo_eq_same_id_returns_true(self) -> None:
        """Verify Todo(id=1) == Todo(id=1) returns True."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")
        assert todo1 == todo2

    def test_todo_eq_different_id_returns_false(self) -> None:
        """Verify Todo(id=1) != Todo(id=2) returns True."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=2, text="Buy milk")
        assert todo1 != todo2

    def test_todo_eq_different_type_returns_false(self) -> None:
        """Verify Todo(id=1) == 'not a todo' returns False."""
        todo = Todo(id=1, text="Buy milk")
        assert todo != "not a todo"

    def test_todo_eq_none_returns_false(self) -> None:
        """Verify Todo(id=1) == None returns False."""
        todo = Todo(id=1, text="Buy milk")
        assert todo is not None
        assert todo != None  # noqa: E711

    def test_todo_eq_id_based_semantics(self) -> None:
        """Verify that equality is based on id only (entity semantics).

        Two todos with same id but different text/done should be equal.
        """
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=1, text="Task B", done=True)
        assert todo1 == todo2

    def test_todo_eq_reflexive(self) -> None:
        """Verify x == x returns True (reflexive property)."""
        todo = Todo(id=1, text="Buy milk")
        assert todo == todo

    def test_todo_eq_symmetric(self) -> None:
        """Verify x == y implies y == x (symmetric property)."""
        todo1 = Todo(id=1, text="Buy milk")
        todo2 = Todo(id=1, text="Buy bread")
        assert todo1 == todo2
        assert todo2 == todo1

    def test_todo_eq_with_object_subclass(self) -> None:
        """Verify comparison with a non-Todo object subclass returns False."""
        todo = Todo(id=1, text="Buy milk")

        class NotATodo:
            pass

        assert todo != NotATodo()
