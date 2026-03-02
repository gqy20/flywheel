"""Test copy/clone method for Todo (issue #6830)."""

import time

import pytest

from flywheel.todo import Todo


class TestTodoCopy:
    """Tests for Todo.copy() method."""

    def test_copy_returns_independent_instance(self):
        """Test that copy() returns a new independent Todo instance."""
        original = Todo(id=1, text="Original task")
        copied = original.copy()

        assert copied is not original
        assert copied.id == original.id
        assert copied.text == original.text
        assert copied.done == original.done

    def test_copy_with_text_override(self):
        """Test that copy() accepts text override via kwargs."""
        original = Todo(id=1, text="Original task")
        copied = original.copy(text="New task")

        assert copied.text == "New task"
        assert original.text == "Original task"
        assert copied.id == original.id

    def test_copy_with_done_override(self):
        """Test that copy() accepts done override via kwargs."""
        original = Todo(id=1, text="Task", done=False)
        copied = original.copy(done=True)

        assert copied.done is True
        assert original.done is False

    def test_copy_with_id_override(self):
        """Test that copy() accepts id override via kwargs."""
        original = Todo(id=1, text="Task")
        copied = original.copy(id=2)

        assert copied.id == 2
        assert original.id == 1

    def test_copy_original_unchanged_after_modification(self):
        """Test that modifying the copy does not affect the original."""
        original = Todo(id=1, text="Original", done=False)
        copied = original.copy(text="Modified", done=True)

        # Modify the copy further
        copied.mark_done()

        # Original should remain unchanged
        assert original.text == "Original"
        assert original.done is False

    def test_copy_has_new_updated_at_timestamp(self):
        """Test that copy has a new updated_at timestamp."""
        original = Todo(id=1, text="Task")
        original_timestamp = original.updated_at

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        copied = original.copy()
        assert copied.updated_at != original_timestamp

    def test_copy_preserves_created_at(self):
        """Test that copy preserves the original created_at timestamp."""
        original = Todo(id=1, text="Task")
        copied = original.copy()

        assert copied.created_at == original.created_at

    def test_copy_with_multiple_overrides(self):
        """Test copy() with multiple field overrides."""
        original = Todo(id=1, text="Task", done=False)
        copied = original.copy(id=2, text="New Task", done=True)

        assert copied.id == 2
        assert copied.text == "New Task"
        assert copied.done is True
        assert original.id == 1
        assert original.text == "Task"
        assert original.done is False

    def test_copy_with_created_at_override(self):
        """Test that created_at can be overridden if needed."""
        original = Todo(id=1, text="Task")
        new_created = "2025-01-01T00:00:00+00:00"
        copied = original.copy(created_at=new_created)

        assert copied.created_at == new_created
        assert original.created_at != new_created

    def test_copy_with_updated_at_override(self):
        """Test that updated_at can be explicitly overridden."""
        original = Todo(id=1, text="Task")
        new_updated = "2025-01-01T00:00:00+00:00"
        copied = original.copy(updated_at=new_updated)

        assert copied.updated_at == new_updated
