"""Tests for issue #4455: Add copy/clone method for immutable-style updates."""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_copy_returns_distinct_object_with_same_values() -> None:
    """copy() should return a new Todo with identical fields (except updated_at)."""
    original = Todo(id=1, text="Buy groceries", done=False)
    original_updated = original.updated_at
    time.sleep(0.001)  # Ensure timestamps differ if updated

    copy = original.copy()

    # Verify it's a distinct object
    assert copy is not original

    # Verify all fields match (except updated_at which is refreshed)
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    # updated_at is automatically refreshed on copy
    assert copy.updated_at >= original_updated


def test_copy_with_text_override_updates_only_text() -> None:
    """copy(text='new') should return new Todo with updated text."""
    original = Todo(id=1, text="original text", done=True)
    original_created = original.created_at
    original_updated = original.updated_at

    copy = original.copy(text="new text")

    # Verify text changed
    assert copy.text == "new text"

    # Verify other fields unchanged
    assert copy.id == original.id
    assert copy.done is True
    assert copy.created_at == original_created

    # Verify updated_at is refreshed (copy is a modification)
    assert copy.updated_at >= original_updated


def test_original_unchanged_after_copy_with_overrides() -> None:
    """Original Todo should be unchanged after copy with overrides."""
    original = Todo(id=1, text="original", done=False)
    original_text = original.text
    original_done = original.done
    original_updated_at = original.updated_at

    # Create a copy with multiple overrides
    _copy = original.copy(text="modified", done=True)

    # Verify original is completely unchanged
    assert original.text == original_text
    assert original.done == original_done
    assert original.updated_at == original_updated_at


def test_copy_with_done_override() -> None:
    """copy(done=True) should update the done status."""
    original = Todo(id=1, text="Task", done=False)
    original_created = original.created_at

    copy = original.copy(done=True)

    assert copy.done is True
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.created_at == original_created


def test_copy_updates_updated_at_timestamp() -> None:
    """copy() should refresh the updated_at timestamp."""
    original = Todo(id=1, text="Task", done=False)
    original_updated = original.updated_at
    time.sleep(0.01)  # Small delay to ensure timestamp differs

    copy = original.copy()

    # Even without overrides, copy is a new instance so updated_at refreshes
    assert copy.updated_at >= original_updated


def test_copy_with_id_override() -> None:
    """copy(id=2) should allow changing the id for new instances."""
    original = Todo(id=1, text="Task", done=True)

    copy = original.copy(id=2)

    assert copy.id == 2
    assert copy.text == original.text
    assert copy.done == original.done


def test_copy_handles_all_dataclass_fields() -> None:
    """copy() should properly handle all dataclass fields including timestamps."""
    original = Todo(id=5, text="Complete task", done=True)
    original_created = original.created_at
    original_updated = original.updated_at
    time.sleep(0.01)

    copy = original.copy()

    # All fields should be preserved except updated_at
    assert copy.id == 5
    assert copy.text == "Complete task"
    assert copy.done is True
    assert copy.created_at == original_created
    assert copy.updated_at >= original_updated


def test_copy_with_multiple_overrides() -> None:
    """copy() should handle multiple field overrides."""
    original = Todo(id=1, text="Original", done=False)

    copy = original.copy(id=2, text="Modified", done=True)

    assert copy.id == 2
    assert copy.text == "Modified"
    assert copy.done is True
    # Original should be unchanged
    assert original.id == 1
    assert original.text == "Original"
    assert original.done is False


def test_copy_with_created_at_override() -> None:
    """copy() should allow overriding created_at if needed."""
    original = Todo(id=1, text="Task")
    new_created_at = "2024-01-01T00:00:00+00:00"

    copy = original.copy(created_at=new_created_at)

    assert copy.created_at == new_created_at
    assert original.created_at != new_created_at


def test_copy_with_updated_at_override() -> None:
    """copy() should allow overriding updated_at if needed."""
    original = Todo(id=1, text="Task")
    new_updated_at = "2024-12-31T23:59:59+00:00"

    copy = original.copy(updated_at=new_updated_at)

    assert copy.updated_at == new_updated_at
    assert original.updated_at != new_updated_at
