"""Regression tests for issue #2988: Todo.copy() method."""

import time

from flywheel.todo import Todo


class TestTodoCopy:
    """Tests for the Todo.copy() method."""

    def test_copy_returns_independent_instance(self) -> None:
        """Test that copy() returns a new independent Todo instance."""
        original = Todo(id=1, text="Original task", done=False)
        copied = original.copy()

        # Verify it's a different instance
        assert copied is not original
        assert isinstance(copied, Todo)

    def test_copy_without_args_preserves_all_fields(self) -> None:
        """Test that copy() without arguments preserves all fields."""
        original = Todo(id=1, text="Task", done=True)
        time.sleep(0.01)  # Ensure timestamp difference
        copied = original.copy()

        assert copied.id == original.id
        assert copied.text == original.text
        assert copied.done == original.done
        assert copied.created_at == original.created_at
        # updated_at should be updated automatically
        assert copied.updated_at != original.updated_at

    def test_copy_with_text_override(self) -> None:
        """Test that copy(text='new') only updates text field."""
        original = Todo(id=1, text="Old text", done=True)
        time.sleep(0.01)
        copied = original.copy(text="New text")

        assert copied.id == original.id
        assert copied.text == "New text"
        assert copied.done == original.done
        assert copied.created_at == original.created_at
        assert copied.updated_at != original.updated_at

    def test_copy_with_done_override(self) -> None:
        """Test that copy(done=True/False) only updates done field."""
        original = Todo(id=1, text="Task", done=False)
        time.sleep(0.01)
        copied = original.copy(done=True)

        assert copied.id == original.id
        assert copied.text == original.text
        assert copied.done is True
        assert original.done is False  # Original unchanged
        assert copied.created_at == original.created_at
        assert copied.updated_at != original.updated_at

    def test_copy_original_unchanged(self) -> None:
        """Test that the original Todo is not affected by copy."""
        original = Todo(id=1, text="Original", done=False)
        original_done = original.done
        original_text = original.text
        original_updated_at = original.updated_at

        original.copy(done=True, text="Modified")

        assert original.done == original_done
        assert original.text == original_text
        assert original.updated_at == original_updated_at

    def test_copy_updates_updated_at_timestamp(self) -> None:
        """Test that copy() automatically updates the updated_at timestamp."""
        original = Todo(id=1, text="Task", done=False)
        original_updated = original.updated_at

        time.sleep(0.01)  # Small delay to ensure timestamp difference
        copied = original.copy()

        assert copied.updated_at > original_updated

    def test_copy_with_multiple_overrides(self) -> None:
        """Test copy() with multiple field overrides."""
        original = Todo(id=1, text="Task", done=False)
        time.sleep(0.01)
        copied = original.copy(text="Updated task", done=True)

        assert copied.id == 1
        assert copied.text == "Updated task"
        assert copied.done is True
        assert copied.updated_at != original.updated_at
