"""Tests for Todo.copy method (Issue #4455).

These tests verify that:
1. todo.copy() returns a new Todo with identical fields
2. todo.copy(text='new') returns new Todo with updated text
3. Original Todo is unchanged after copy with overrides
4. copy() properly handles all dataclass fields including timestamps
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_distinct_object_with_same_values() -> None:
    """copy() should return a new distinct object with the same values."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Should be a different object
    assert copied is not original
    # Should have same values
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should update only the text field."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread")

    # Copied should have new text
    assert copied.text == "buy bread"
    # Other fields should remain same
    assert copied.id == original.id
    assert copied.done == original.done


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should update only the done field."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(done=True)

    # Copied should have done=True
    assert copied.done is True
    # Other fields should remain same
    assert copied.id == original.id
    assert copied.text == original.text


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should handle multiple field overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread", done=True)

    assert copied.text == "buy bread"
    assert copied.done is True
    assert copied.id == original.id


def test_todo_original_unchanged_after_copy() -> None:
    """Original Todo should be unchanged after copy with overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    original_text = original.text
    original_done = original.done

    original.copy(text="buy bread", done=True)

    # Original should be unchanged
    assert original.text == original_text
    assert original.done == original_done


def test_todo_copy_updates_updated_at_timestamp() -> None:
    """copy() should update the updated_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    original_updated_at = original.updated_at

    copied = original.copy(text="new text")

    # Copied should have a new updated_at timestamp
    assert copied.updated_at != original_updated_at


def test_todo_copy_preserves_created_at() -> None:
    """copy() should preserve the original created_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    original_created_at = original.created_at

    copied = original.copy(text="new text")

    # Copied should have same created_at as original
    assert copied.created_at == original_created_at


def test_todo_copy_with_id_override() -> None:
    """copy() should allow overriding the id field."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(id=42)

    assert copied.id == 42
    assert copied.text == original.text
    assert copied.done == original.done
