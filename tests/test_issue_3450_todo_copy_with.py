"""Tests for Issue #3450: Todo copy_with method for immutable updates."""

from __future__ import annotations

import time

from flywheel.todo import Todo


class TestTodoCopyWith:
    """Test suite for Todo.copy_with() method supporting immutable updates."""

    def test_copy_with_returns_new_instance_original_unchanged(self) -> None:
        """Test that copy_with returns a new Todo instance without modifying the original."""
        original = Todo(id=1, text="original task")
        original_created = original.created_at
        original_updated = original.updated_at

        # Small delay to ensure updated_at differs
        time.sleep(0.01)

        new_todo = original.copy_with(done=True)

        # Original should be unchanged
        assert original.done is False
        assert original.text == "original task"
        assert original.id == 1
        assert original.created_at == original_created
        assert original.updated_at == original_updated

        # New instance should be different object
        assert new_todo is not original

    def test_copy_with_overrides_specified_fields(self) -> None:
        """Test that copy_with correctly overrides specified fields."""
        original = Todo(id=1, text="task a", done=False)
        new_todo = original.copy_with(done=True)

        # New todo should have overridden done field
        assert new_todo.done is True
        # Other fields should match original
        assert new_todo.id == 1
        assert new_todo.text == "task a"

    def test_copy_with_preserves_unspecified_fields(self) -> None:
        """Test that unspecified fields are preserved from the original."""
        original = Todo(id=5, text="preserved text", done=True)
        new_todo = original.copy_with(text="new text")

        # Overridden field
        assert new_todo.text == "new text"
        # Preserved fields
        assert new_todo.id == 5
        assert new_todo.done is True
        assert new_todo.created_at == original.created_at

    def test_copy_with_updates_updated_at_timestamp(self) -> None:
        """Test that copy_with automatically updates the updated_at timestamp."""
        original = Todo(id=1, text="task")
        original_updated = original.updated_at

        # Small delay to ensure timestamp differs
        time.sleep(0.01)

        new_todo = original.copy_with(done=True)

        # New todo should have a newer updated_at
        assert new_todo.updated_at > original_updated
        # Original should still have old updated_at
        assert original.updated_at == original_updated

    def test_copy_with_preserves_created_at(self) -> None:
        """Test that copy_with preserves the original created_at timestamp."""
        original = Todo(id=1, text="task")
        original_created = original.created_at

        time.sleep(0.01)

        new_todo = original.copy_with(done=True)

        # created_at should be preserved
        assert new_todo.created_at == original_created

    def test_copy_with_can_override_multiple_fields(self) -> None:
        """Test that copy_with can override multiple fields at once."""
        original = Todo(id=1, text="original", done=False)
        new_todo = original.copy_with(text="modified", done=True)

        assert new_todo.text == "modified"
        assert new_todo.done is True
        assert new_todo.id == 1  # Unchanged

    def test_copy_with_can_override_id(self) -> None:
        """Test that copy_with can override the id field."""
        original = Todo(id=1, text="task")
        new_todo = original.copy_with(id=2)

        assert new_todo.id == 2
        assert original.id == 1

    def test_copy_with_no_args_returns_copy_with_updated_timestamp(self) -> None:
        """Test that copy_with() with no args returns a copy with only updated_at changed."""
        original = Todo(id=1, text="task", done=True)
        original_updated = original.updated_at

        time.sleep(0.01)

        new_todo = original.copy_with()

        # All fields should match except updated_at
        assert new_todo.id == original.id
        assert new_todo.text == original.text
        assert new_todo.done == original.done
        assert new_todo.created_at == original.created_at
        assert new_todo.updated_at > original_updated

    def test_copy_with_integration_with_undo_pattern(self) -> None:
        """Test copy_with in a typical undo/snapshot pattern."""
        # Simulate a sequence of immutable updates
        history: list[Todo] = []

        t1 = Todo(id=1, text="task")
        history.append(t1)

        t2 = t1.copy_with(done=True)
        history.append(t2)

        t3 = t2.copy_with(text="completed task")
        history.append(t3)

        # Each version in history should be preserved
        assert history[0].done is False
        assert history[0].text == "task"

        assert history[1].done is True
        assert history[1].text == "task"

        assert history[2].done is True
        assert history[2].text == "completed task"
