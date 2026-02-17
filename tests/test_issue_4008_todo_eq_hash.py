"""Test for issue #4008: Todo __eq__ and __hash__ methods."""


class TestTodoEquality:
    """Test Todo equality comparison."""

    def test_todos_with_same_id_and_text_are_equal(self):
        """Todo(1, 'a') == Todo(1, 'a') returns True."""
        from flywheel.todo import Todo

        todo1 = Todo(1, "a")
        todo2 = Todo(1, "a")
        assert todo1 == todo2

    def test_todos_with_different_id_are_not_equal(self):
        """Todo(1, 'a') != Todo(2, 'a') returns True."""
        from flywheel.todo import Todo

        todo1 = Todo(1, "a")
        todo2 = Todo(2, "a")
        assert todo1 != todo2

    def test_todos_with_different_text_are_not_equal(self):
        """Todos with same id but different text are not equal."""
        from flywheel.todo import Todo

        todo1 = Todo(1, "a")
        todo2 = Todo(1, "b")
        assert todo1 != todo2

    def test_todos_with_different_done_status_are_not_equal(self):
        """Todos with same id but different done status are not equal."""
        from flywheel.todo import Todo

        todo1 = Todo(1, "a", done=False)
        todo2 = Todo(1, "a", done=True)
        assert todo1 != todo2


class TestTodoHash:
    """Test Todo hash support for set/dict usage."""

    def test_hash_of_todo_does_not_raise(self):
        """hash(Todo) does not raise TypeError."""
        from flywheel.todo import Todo

        todo = Todo(1, "a")
        # This should not raise TypeError
        hash(todo)

    def test_todos_in_set(self):
        """Todo objects can be added to a set."""
        from flywheel.todo import Todo

        todo1 = Todo(1, "a")
        todo2 = Todo(1, "a")  # Same as todo1
        todo3 = Todo(2, "b")  # Different

        todo_set = {todo1, todo2, todo3}
        # With hash based on id, todo1 and todo2 have same hash
        # and are equal, so set should have 2 elements
        assert len(todo_set) == 2

    def test_todos_as_dict_keys(self):
        """Todo objects can be used as dict keys."""
        from flywheel.todo import Todo

        todo1 = Todo(1, "a")
        todo2 = Todo(2, "b")

        mapping = {todo1: "first", todo2: "second"}
        assert mapping[todo1] == "first"
        assert mapping[todo2] == "second"
