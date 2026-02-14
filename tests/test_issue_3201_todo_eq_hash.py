"""Tests for Todo __eq__ and __hash__ methods (issue #3201)."""

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todos_with_same_fields_are_equal(self):
        """Two Todo instances with identical fields should be equal."""
        todo1 = Todo(id=1, text="Buy groceries", done=False)
        todo2 = Todo(id=1, text="Buy groceries", done=False)

        # Explicitly set timestamps to be identical
        todo1.created_at = "2026-01-01T00:00:00+00:00"
        todo1.updated_at = "2026-01-01T00:00:00+00:00"
        todo2.created_at = "2026-01-01T00:00:00+00:00"
        todo2.updated_at = "2026-01-01T00:00:00+00:00"

        assert todo1 == todo2

    def test_todos_with_different_id_are_not_equal(self):
        """Todos with different ids should not be equal."""
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=2, text="Task A", done=False)

        assert todo1 != todo2

    def test_todos_with_different_text_are_not_equal(self):
        """Todos with different text should not be equal."""
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=1, text="Task B", done=False)

        assert todo1 != todo2

    def test_todos_with_different_done_are_not_equal(self):
        """Todos with different done status should not be equal."""
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=1, text="Task A", done=True)

        assert todo1 != todo2

    def test_todos_with_different_created_at_are_not_equal(self):
        """Todos with different created_at timestamps should not be equal."""
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=1, text="Task A", done=False)

        todo1.created_at = "2026-01-01T00:00:00+00:00"
        todo2.created_at = "2026-01-02T00:00:00+00:00"

        assert todo1 != todo2

    def test_todos_with_different_updated_at_are_not_equal(self):
        """Todos with different updated_at timestamps should not be equal."""
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=1, text="Task A", done=False)

        todo1.updated_at = "2026-01-01T00:00:00+00:00"
        todo2.updated_at = "2026-01-02T00:00:00+00:00"

        assert todo1 != todo2

    def test_todo_not_equal_to_none(self):
        """A Todo should not be equal to None."""
        todo = Todo(id=1, text="Task A")
        assert todo != None  # noqa: E711

    def test_todo_not_equal_to_other_type(self):
        """A Todo should not be equal to objects of other types."""
        todo = Todo(id=1, text="Task A")
        assert todo != "Todo(id=1, text='Task A', done=False)"
        assert todo != {"id": 1, "text": "Task A", "done": False}


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todo_can_be_added_to_set(self):
        """A Todo should be hashable and usable in a set."""
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=1, text="Task A", done=False)

        # Set timestamps to be identical
        todo1.created_at = "2026-01-01T00:00:00+00:00"
        todo1.updated_at = "2026-01-01T00:00:00+00:00"
        todo2.created_at = "2026-01-01T00:00:00+00:00"
        todo2.updated_at = "2026-01-01T00:00:00+00:00"

        todo_set = {todo1, todo2}
        assert len(todo_set) == 1  # Duplicate should be removed

    def test_todos_with_same_id_deduplicate_in_set(self):
        """Multiple Todos with same id should deduplicate in a set."""
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=1, text="Task A", done=False)
        todo3 = Todo(id=2, text="Task B", done=False)

        # Set timestamps to be identical for todos 1 and 2
        todo1.created_at = "2026-01-01T00:00:00+00:00"
        todo1.updated_at = "2026-01-01T00:00:00+00:00"
        todo2.created_at = "2026-01-01T00:00:00+00:00"
        todo2.updated_at = "2026-01-01T00:00:00+00:00"

        todo_set = {todo1, todo2, todo3}
        assert len(todo_set) == 2

    def test_todo_can_be_dict_key(self):
        """A Todo should be usable as a dictionary key."""
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=1, text="Task A", done=False)

        # Set timestamps to be identical
        todo1.created_at = "2026-01-01T00:00:00+00:00"
        todo1.updated_at = "2026-01-01T00:00:00+00:00"
        todo2.created_at = "2026-01-01T00:00:00+00:00"
        todo2.updated_at = "2026-01-01T00:00:00+00:00"

        todo_dict = {todo1: "value1"}
        todo_dict[todo2] = "value2"

        assert len(todo_dict) == 1
        assert todo_dict[todo1] == "value2"

    def test_equal_todos_have_same_hash(self):
        """Two equal Todo instances should have the same hash."""
        todo1 = Todo(id=1, text="Task A", done=False)
        todo2 = Todo(id=1, text="Task A", done=False)

        # Set timestamps to be identical
        todo1.created_at = "2026-01-01T00:00:00+00:00"
        todo1.updated_at = "2026-01-01T00:00:00+00:00"
        todo2.created_at = "2026-01-01T00:00:00+00:00"
        todo2.updated_at = "2026-01-01T00:00:00+00:00"

        assert hash(todo1) == hash(todo2)
