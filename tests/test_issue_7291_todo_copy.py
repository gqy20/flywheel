"""Tests for Todo.copy() method - Issue #7291."""

import time

from flywheel.todo import Todo


class TestTodoCopy:
    """Test suite for Todo.copy() method."""

    def test_todo_copy_creates_new_instance(self):
        """Verify copy returns a different object instance."""
        original = Todo(id=1, text="Test todo", done=False)
        copied = original.copy()

        assert copied is not original
        assert isinstance(copied, Todo)

    def test_todo_copy_preserves_content(self):
        """Verify copy preserves text and done status."""
        original = Todo(id=1, text="Test todo", done=True)
        copied = original.copy()

        assert copied.text == original.text
        assert copied.done == original.done

    def test_todo_copy_new_timestamps(self):
        """Verify copy generates new timestamps."""
        original = Todo(id=1, text="Test todo", done=False)
        # Small delay to ensure different timestamps
        time.sleep(0.01)
        copied = original.copy()

        # With with_id=False (default), timestamps should be new
        assert copied.created_at != original.created_at
        assert copied.updated_at != original.updated_at

    def test_todo_copy_with_id_false(self):
        """Verify with_id=False generates new id (id=0)."""
        original = Todo(id=1, text="Test todo", done=False)
        copied = original.copy(with_id=False)

        # with_id=False should set id to 0 for caller to handle
        assert copied.id == 0

    def test_todo_copy_with_id_true(self):
        """Verify with_id=True preserves original id."""
        original = Todo(id=1, text="Test todo", done=False)
        copied = original.copy(with_id=True)

        assert copied.id == original.id

    def test_todo_copy_independence(self):
        """Verify modifying copy doesn't affect original."""
        original = Todo(id=1, text="Original text", done=False)
        copied = original.copy()

        # Modify copied instance
        copied.text = "Modified text"
        copied.done = True

        # Original should remain unchanged
        assert original.text == "Original text"
        assert original.done is False

    def test_todo_copy_with_id_true_preserves_timestamps(self):
        """Verify with_id=True preserves original timestamps."""
        original = Todo(id=1, text="Test todo", done=False)
        time.sleep(0.01)
        copied = original.copy(with_id=True)

        # with_id=True should preserve timestamps as well
        assert copied.created_at == original.created_at
        assert copied.updated_at == original.updated_at
