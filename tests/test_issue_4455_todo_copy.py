"""Tests for Todo.copy method (Issue #4455).

These tests verify that:
1. todo.copy() returns a new Todo with identical fields
2. todo.copy(text='new') returns new Todo with updated text
3. Original Todo is unchanged after copy with overrides
4. copy() properly handles all dataclass fields including timestamps
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_returns_distinct_object_with_same_values() -> None:
    """copy() should return a distinct object with the same values."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    # Should be a different object
    assert copy is not original

    # Should have the same values
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should update only the text field."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy(text="buy bread")

    # Copy should have new text
    assert copy.text == "buy bread"

    # Other fields should remain the same
    assert copy.id == original.id
    assert copy.done == original.done


def test_todo_copy_with_done_override() -> None:
    """copy(done=True/False) should update only the done field."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(done=True)

    # Copy should have done=True
    assert copy.done is True

    # Other fields should remain the same
    assert copy.id == original.id
    assert copy.text == original.text


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should handle multiple field overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(text="buy bread", done=True, id=42)

    assert copy.text == "buy bread"
    assert copy.done is True
    assert copy.id == 42


def test_todo_original_unchanged_after_copy() -> None:
    """Original Todo should be unchanged after copy with overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    original_id = original.id
    original_text = original.text
    original_done = original.done

    # Create a copy with overrides
    original.copy(text="buy bread", done=True, id=99)

    # Original should be unchanged
    assert original.id == original_id
    assert original.text == original_text
    assert original.done == original_done


def test_todo_copy_updates_updated_at_timestamp() -> None:
    """copy() should update the updated_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    time.sleep(0.01)  # Small delay to ensure different timestamp

    copy = original.copy()

    # Copy should have a different (newer) updated_at
    assert copy.updated_at != original.updated_at
    # created_at should remain the same
    assert copy.created_at == original.created_at


def test_todo_copy_preserves_timestamps_when_explicitly_overridden() -> None:
    """copy() should allow explicit timestamp overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    custom_time = "2024-01-01T00:00:00+00:00"

    copy = original.copy(updated_at=custom_time, created_at=custom_time)

    assert copy.updated_at == custom_time
    assert copy.created_at == custom_time


def test_todo_copy_with_all_fields() -> None:
    """copy() should work with all dataclass fields."""
    original = Todo(
        id=1,
        text="buy milk",
        done=True,
        created_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-02T00:00:00+00:00",
    )

    copy = original.copy()

    # All fields should match
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    # updated_at will be different since copy() updates it


def test_todo_copy_enables_immutability_pattern() -> None:
    """copy() should enable immutable-style programming patterns."""
    # Functional-style update: create modified copy instead of mutating
    original = Todo(id=1, text="buy milk", done=False)

    # "Update" by creating a new object
    modified = original.copy(done=True)

    # Original unchanged
    assert original.done is False
    # Modified has the change
    assert modified.done is True
