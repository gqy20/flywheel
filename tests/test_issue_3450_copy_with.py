"""Tests for Todo.copy_with immutable update method.

Issue #3450: Add copy/clone method to support immutable mode updates.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoCopyWith:
    """Tests for the Todo.copy_with() method."""

    def test_copy_with_done_returns_new_todo_with_done_true(self) -> None:
        """copy_with(done=True) should return new Todo with done=True."""
        t1 = Todo(id=1, text="a")
        t2 = t1.copy_with(done=True)

        # New object should have done=True
        assert t2.done is True
        assert t2.id == t1.id
        assert t2.text == "a"

    def test_copy_with_leaves_original_unchanged(self) -> None:
        """Original Todo should remain unchanged after copy_with."""
        t1 = Todo(id=1, text="a", done=False)
        original_created_at = t1.created_at
        original_updated_at = t1.updated_at

        t2 = t1.copy_with(done=True)

        # Original should be unchanged
        assert t1.done is False
        assert t1.text == "a"
        assert t1.created_at == original_created_at
        assert t1.updated_at == original_updated_at

    def test_copy_with_updates_timestamp(self) -> None:
        """New Todo's updated_at should be updated to current time."""
        t1 = Todo(id=1, text="a")
        original_updated_at = t1.updated_at

        t2 = t1.copy_with(done=True)

        # New Todo should have updated timestamp
        assert t2.updated_at >= original_updated_at

    def test_copy_with_preserves_unspecified_fields(self) -> None:
        """Fields not specified in kwargs should be copied from original."""
        t1 = Todo(id=42, text="original task", done=False)

        t2 = t1.copy_with(done=True)

        # id and text should be preserved
        assert t2.id == 42
        assert t2.text == "original task"
        assert t2.done is True

    def test_copy_with_can_override_text(self) -> None:
        """copy_with should allow overriding text field."""
        t1 = Todo(id=1, text="old text")

        t2 = t1.copy_with(text="new text")

        assert t2.text == "new text"
        assert t1.text == "old text"

    def test_copy_with_can_override_multiple_fields(self) -> None:
        """copy_with should allow overriding multiple fields at once."""
        t1 = Todo(id=1, text="old", done=False)

        t2 = t1.copy_with(text="new", done=True)

        assert t2.text == "new"
        assert t2.done is True
        assert t1.text == "old"
        assert t1.done is False

    def test_copy_with_no_args_returns_copy(self) -> None:
        """copy_with() with no args should return a copy with updated timestamp."""
        t1 = Todo(id=1, text="task")
        original_updated_at = t1.updated_at

        t2 = t1.copy_with()

        # Should be a different object
        assert t2 is not t1
        # Same values (except updated_at)
        assert t2.id == t1.id
        assert t2.text == t1.text
        assert t2.done == t1.done
        # Timestamp should be updated
        assert t2.updated_at >= original_updated_at

    def test_copy_with_can_override_id(self) -> None:
        """copy_with should allow overriding id field."""
        t1 = Todo(id=1, text="task")

        t2 = t1.copy_with(id=99)

        assert t2.id == 99
        assert t1.id == 1

    def test_copy_with_preserves_created_at(self) -> None:
        """copy_with should preserve the original created_at timestamp."""
        t1 = Todo(id=1, text="task")
        original_created_at = t1.created_at

        t2 = t1.copy_with(done=True)

        # created_at should be preserved from original
        assert t2.created_at == original_created_at

    def test_copy_with_can_set_created_at_explicitly(self) -> None:
        """copy_with should allow explicit override of created_at if specified."""
        t1 = Todo(id=1, text="task")

        t2 = t1.copy_with(created_at="2020-01-01T00:00:00+00:00")

        assert t2.created_at == "2020-01-01T00:00:00+00:00"
