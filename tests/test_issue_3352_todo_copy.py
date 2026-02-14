"""Test for issue #3352: Todo copy/clone method."""

from flywheel.todo import Todo


class TestTodoCopy:
    """Tests for Todo.copy() method."""

    def test_copy_returns_equal_todo(self):
        """todo.copy() returns a new object with equal values."""
        original = Todo(id=1, text="a")
        copy = original.copy()

        assert copy.id == original.id
        assert copy.text == original.text
        assert copy.done == original.done
        assert copy.created_at == original.created_at
        assert copy.updated_at == original.updated_at
        # Ensure it's a different object
        assert copy is not original

    def test_copy_with_text_override(self):
        """todo.copy(text='new') returns a new object with modified text."""
        original = Todo(id=1, text="a")
        copy = original.copy(text="b")

        assert copy.text == "b"
        assert copy.id == original.id  # Other fields preserved
        assert copy.done == original.done

    def test_copy_with_multiple_overrides(self):
        """todo.copy() supports overriding multiple fields."""
        original = Todo(id=1, text="a", done=False)
        copy = original.copy(text="b", done=True)

        assert copy.text == "b"
        assert copy.done is True
        assert copy.id == original.id  # Non-overridden fields preserved

    def test_copy_preserves_original(self):
        """Copying does not modify the original object."""
        original = Todo(id=1, text="original")
        original.copy(text="modified")

        assert original.text == "original"  # Original unchanged

    def test_copy_with_done_override(self):
        """todo.copy(done=True) returns a new object with modified done status."""
        original = Todo(id=1, text="a", done=False)
        copy = original.copy(done=True)

        assert copy.done is True
        assert original.done is False  # Original unchanged

    def test_copy_with_id_override(self):
        """todo.copy(id=2) returns a new object with modified id."""
        original = Todo(id=1, text="a")
        copy = original.copy(id=2)

        assert copy.id == 2
        assert original.id == 1  # Original unchanged
