"""Test Todo.copy() method for issue #6341."""

import time

from flywheel.todo import Todo


class TestTodoCopy:
    """Test cases for Todo.copy() method."""

    def test_copy_returns_different_object_instance(self):
        """copy() should return a new Todo instance, not the same object."""
        original = Todo(id=1, text="Test todo")
        copy = original.copy()

        assert copy is not original, "copy() should return a different object instance"

    def test_copy_preserves_text_and_done(self):
        """copy() should preserve text and done status."""
        original = Todo(id=1, text="Original text", done=True)
        copy = original.copy()

        assert copy.text == original.text, "copy() should preserve text"
        assert copy.done == original.done, "copy() should preserve done status"

    def test_copy_modification_does_not_affect_original(self):
        """Modifying the copy should not affect the original."""
        original = Todo(id=1, text="Original text")
        copy = original.copy()

        copy.rename("Modified text")
        copy.mark_done()

        assert original.text == "Original text", "Original text should not change"
        assert original.done is False, "Original done status should not change"

    def test_copy_generates_new_timestamps(self):
        """copy() should generate new created_at and updated_at timestamps."""
        original = Todo(id=1, text="Test todo")
        original_created_at = original.created_at
        original_updated_at = original.updated_at

        # Small delay to ensure timestamps differ
        time.sleep(0.01)

        copy = original.copy()

        assert copy.created_at != original_created_at, "copy() should generate new created_at"
        assert copy.updated_at != original_updated_at, "copy() should generate new updated_at"

    def test_copy_default_generates_new_id(self):
        """copy() without arguments should generate a new id (default 0 or auto)."""
        original = Todo(id=42, text="Test todo")
        copy = original.copy()

        # By default, copy should have id=0 (or a new id, not the original)
        assert copy.id == 0, "copy() should default to id=0 for new instance"

    def test_copy_with_explicit_new_id(self):
        """copy(new_id=X) should use the provided id."""
        original = Todo(id=1, text="Test todo")
        copy = original.copy(new_id=99)

        assert copy.id == 99, "copy(new_id=99) should set id to 99"

    def test_copy_done_state_preserved(self):
        """copy() should preserve the done state for both True and False."""
        # Test with done=False
        original_not_done = Todo(id=1, text="Not done", done=False)
        copy_not_done = original_not_done.copy(new_id=2)
        assert copy_not_done.done is False, "copy() should preserve done=False"

        # Test with done=True
        original_done = Todo(id=3, text="Done", done=True)
        copy_done = original_done.copy(new_id=4)
        assert copy_done.done is True, "copy() should preserve done=True"
