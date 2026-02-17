"""Tests for issue #4036: update() method for batch updating Todo attributes."""

import time

import pytest

from flywheel.todo import Todo


class TestTodoUpdateMethod:
    """Test cases for Todo.update() method."""

    def test_update_text_only(self):
        """Test update(text='new') only updates text."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        # Small delay to ensure updated_at would differ
        time.sleep(0.01)

        todo.update(text="new text")

        assert todo.text == "new text"
        assert todo.done is False  # unchanged
        assert todo.updated_at != original_updated_at

    def test_update_done_only(self):
        """Test update(done=True) only updates done status."""
        todo = Todo(id=1, text="original", done=False)
        original_updated_at = todo.updated_at
        original_text = todo.text

        time.sleep(0.01)

        todo.update(done=True)

        assert todo.done is True
        assert todo.text == original_text  # unchanged
        assert todo.updated_at != original_updated_at

    def test_update_both_text_and_done(self):
        """Test update(text='new', done=True) updates both fields."""
        todo = Todo(id=1, text="original", done=False)
        original_updated_at = todo.updated_at

        time.sleep(0.01)

        todo.update(text="new text", done=True)

        assert todo.text == "new text"
        assert todo.done is True
        assert todo.updated_at != original_updated_at

    def test_update_no_args_does_not_modify(self):
        """Test update() with no arguments does not modify any field."""
        todo = Todo(id=1, text="original", done=False)
        original_updated_at = todo.updated_at
        original_text = todo.text
        original_done = todo.done

        time.sleep(0.01)

        todo.update()

        assert todo.text == original_text
        assert todo.done == original_done
        assert todo.updated_at == original_updated_at

    def test_update_empty_text_raises_error(self):
        """Test update(text='') raises ValueError (consistent with rename())."""
        todo = Todo(id=1, text="original")

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.update(text="")

    def test_update_whitespace_text_raises_error(self):
        """Test update(text='   ') raises ValueError (consistent with rename())."""
        todo = Todo(id=1, text="original")

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.update(text="   ")

    def test_update_done_false(self):
        """Test update(done=False) sets done to False."""
        todo = Todo(id=1, text="original", done=True)
        original_updated_at = todo.updated_at

        time.sleep(0.01)

        todo.update(done=False)

        assert todo.done is False
        assert todo.updated_at != original_updated_at

    def test_update_single_updated_at_timestamp(self):
        """Test that update() with multiple changes only updates updated_at once."""
        todo = Todo(id=1, text="original", done=False)
        original_updated_at = todo.updated_at

        time.sleep(0.01)

        # When updating both text and done, updated_at should be set once
        todo.update(text="new", done=True)

        # updated_at should be different from original
        assert todo.updated_at != original_updated_at
        # Text and done should both be updated
        assert todo.text == "new"
        assert todo.done is True
