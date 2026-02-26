"""Tests for Todo.__eq__ and __hash__ support (Issue #5958)."""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoEquality:
    """Tests for Todo.__eq__ method."""

    def test_todos_with_same_id_are_equal(self) -> None:
        """Two Todo objects with the same id should be equal."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="a")
        assert todo1 == todo2

    def test_todos_with_same_id_different_text_are_equal(self) -> None:
        """Equality should be based on id only, not text or other fields."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")
        assert todo1 == todo2

    def test_todos_with_different_id_are_not_equal(self) -> None:
        """Two Todo objects with different ids should not be equal."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=2, text="a")
        assert todo1 != todo2

    def test_todo_not_equal_to_non_todo(self) -> None:
        """A Todo should not be equal to a non-Todo object."""
        todo = Todo(id=1, text="a")
        assert todo != "not a todo"
        assert todo != 1
        assert todo != {"id": 1, "text": "a"}
        assert todo != None  # noqa: E711


class TestTodoHash:
    """Tests for Todo.__hash__ method."""

    def test_todos_with_same_id_have_same_hash(self) -> None:
        """Two Todo objects with the same id should have the same hash."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="a")
        assert hash(todo1) == hash(todo2)

    def test_todos_with_different_id_have_different_hash(self) -> None:
        """Two Todo objects with different ids should have different hashes."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=2, text="a")
        # Hashes may theoretically collide, but for sequential small integers they won't
        assert hash(todo1) != hash(todo2)

    def test_todos_can_be_used_in_set(self) -> None:
        """Todo objects should be usable in a set."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")  # Same id as todo1
        todo3 = Todo(id=2, text="c")

        todo_set = {todo1, todo2, todo3}
        # Should have 2 unique todos (todo1 and todo2 have same id, todo3 has different)
        assert len(todo_set) == 2

    def test_todos_can_be_used_as_dict_keys(self) -> None:
        """Todo objects should be usable as dictionary keys."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")  # Same id as todo1
        todo3 = Todo(id=2, text="c")

        d = {todo1: "first", todo2: "second", todo3: "third"}
        # Should have 2 unique keys (todo1 and todo2 have same id)
        assert len(d) == 2

    def test_set_deduplication_based_on_id(self) -> None:
        """Set should deduplicate todos based on id."""
        todos = [
            Todo(id=1, text="task one"),
            Todo(id=1, text="task one updated"),  # Same id, different text
            Todo(id=2, text="task two"),
            Todo(id=2, text="task two updated"),  # Same id, different text
            Todo(id=3, text="task three"),
        ]
        unique_todos = set(todos)
        assert len(unique_todos) == 3

    def test_hash_is_consistent(self) -> None:
        """Hash should be consistent for the same object."""
        todo = Todo(id=1, text="a")
        hash1 = hash(todo)
        hash2 = hash(todo)
        assert hash1 == hash2

    def test_hash_based_on_id_only(self) -> None:
        """Hash should be based only on id, not on text or other fields."""
        todo1 = Todo(id=1, text="a")
        todo2 = Todo(id=1, text="b")  # Same id, different text
        assert hash(todo1) == hash(todo2)
