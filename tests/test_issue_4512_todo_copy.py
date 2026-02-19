"""Tests for Todo.copy() method - Issue #4512.

Feature: Add Todo.copy() or update() method to support partial field updates.
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


class TestTodoCopyBasic:
    """Basic copy functionality tests."""

    def test_copy_returns_different_object_with_same_fields(self) -> None:
        """copy() should return a new Todo with all fields identical."""
        original = Todo(id=1, text="original task", done=False)
        copied = original.copy()

        # Different objects
        assert copied is not original

        # Same field values
        assert copied.id == original.id
        assert copied.text == original.text
        assert copied.done == original.done
        assert copied.created_at == original.created_at

    def test_copy_does_not_modify_original(self) -> None:
        """copy() with overrides should not affect the original Todo."""
        original = Todo(id=1, text="original task", done=False)
        original_text = original.text
        original_done = original.done
        original_updated_at = original.updated_at

        copied = original.copy(text="new text", done=True)

        # Original should be unchanged
        assert original.text == original_text
        assert original.done == original_done
        assert original.updated_at == original_updated_at

        # Copied should have new values
        assert copied.text == "new text"
        assert copied.done is True

    def test_copy_with_text_override(self) -> None:
        """copy(text='x') should update only the text field."""
        original = Todo(id=1, text="old text")
        copied = original.copy(text="new text")

        assert copied.text == "new text"
        assert copied.id == original.id
        assert copied.done == original.done

    def test_copy_with_done_override(self) -> None:
        """copy(done=True) should update only the done field."""
        original = Todo(id=1, text="task", done=False)
        copied = original.copy(done=True)

        assert copied.done is True
        assert copied.text == original.text
        assert copied.id == original.id

    def test_copy_with_multiple_overrides(self) -> None:
        """copy() should handle multiple field overrides."""
        original = Todo(id=1, text="task", done=False)
        copied = original.copy(text="updated", done=True)

        assert copied.text == "updated"
        assert copied.done is True
        assert copied.id == original.id


class TestTodoCopyTimestamp:
    """Timestamp handling in copy()."""

    def test_copy_updates_updated_at_timestamp(self) -> None:
        """copy() should automatically refresh updated_at timestamp."""
        original = Todo(id=1, text="task")
        original_updated = original.updated_at

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        copied = original.copy()

        # Copied should have a newer updated_at
        assert copied.updated_at >= original_updated

    def test_copy_preserves_created_at(self) -> None:
        """copy() should preserve the original created_at timestamp."""
        original = Todo(id=1, text="task")
        copied = original.copy(text="new text")

        assert copied.created_at == original.created_at

    def test_copy_allows_explicit_updated_at_override(self) -> None:
        """copy(updated_at=...) should allow explicit timestamp override."""
        original = Todo(id=1, text="task")
        explicit_time = "2024-01-01T00:00:00+00:00"

        copied = original.copy(updated_at=explicit_time)

        assert copied.updated_at == explicit_time


class TestTodoCopyEdgeCases:
    """Edge case tests for copy()."""

    def test_copy_with_id_override(self) -> None:
        """copy() should allow id override for creating new todos."""
        original = Todo(id=1, text="task")
        copied = original.copy(id=99)

        assert copied.id == 99
        assert original.id == 1

    def test_copy_with_created_at_override(self) -> None:
        """copy() should allow created_at override."""
        original = Todo(id=1, text="task")
        new_created = "2024-01-01T00:00:00+00:00"

        copied = original.copy(created_at=new_created)

        assert copied.created_at == new_created

    def test_copy_chain_multiple_copies(self) -> None:
        """copy() should work in a chain."""
        original = Todo(id=1, text="v1", done=False)

        v2 = original.copy(text="v2")
        v3 = v2.copy(done=True)
        v4 = v3.copy(id=999)

        assert original.text == "v1"
        assert original.done is False
        assert original.id == 1

        assert v4.text == "v2"
        assert v4.done is True
        assert v4.id == 999
