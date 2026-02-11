"""Tests for Todo.copy() method (Issue #2859).

These tests verify that:
1. Todo.copy() creates an independent copy of the todo
2. copy(text=...) overrides the text field
3. copy(done=...) overrides the done field
4. Original todo is unchanged after copy operations
5. Multiple field overrides work together
6. Copied instance gets new updated_at timestamp
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_creates_independent_instance() -> None:
    """copy() should create a new Todo instance with the same values."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Should be different objects
    assert copied is not original

    # Should have same values
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should return new Todo with updated text."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread")

    # Original unchanged
    assert original.text == "buy milk"

    # Copy has new text
    assert copied.text == "buy bread"
    # Other fields preserved
    assert copied.id == original.id
    assert copied.done == original.done


def test_todo_copy_with_done_override() -> None:
    """copy(done=...) should return new Todo with updated done status."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(done=True)

    # Original unchanged
    assert original.done is False

    # Copy has new done status
    assert copied.done is True
    # Other fields preserved
    assert copied.id == original.id
    assert copied.text == original.text


def test_todo_copy_original_unchanged() -> None:
    """Original todo should remain unchanged after copy operations."""
    original = Todo(id=1, text="original text", done=False)
    original_updated_at = original.updated_at

    # Create copies with modifications (just to verify they don't affect original)
    _ = original.copy(text="modified text")
    _ = original.copy(done=True)

    # Original should have all original values
    assert original.id == 1
    assert original.text == "original text"
    assert original.done is False
    assert original.updated_at == original_updated_at


def test_todo_copy_with_both_overrides() -> None:
    """copy() should support multiple field overrides at once."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy eggs", done=True)

    # Original unchanged
    assert original.text == "buy milk"
    assert original.done is False

    # Copy has both fields updated
    assert copied.text == "buy eggs"
    assert copied.done is True
    assert copied.id == original.id


def test_todo_copy_updates_timestamps() -> None:
    """Copied instance should have a new updated_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)

    # Give some time for timestamps to differ
    import time
    time.sleep(0.01)

    copied = original.copy()

    # created_at should be preserved
    assert copied.created_at == original.created_at

    # updated_at should be newer or different
    # (at minimum, the copy should get a fresh timestamp)
    assert copied.updated_at != original.updated_at
