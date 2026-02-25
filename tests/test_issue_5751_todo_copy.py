"""Tests for Todo.copy() method - Issue #5751.

Add copy/clone method to Todo for creating modified copies without mutating originals.
Useful for undo operations, preview changes, and functional programming patterns.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_copy_returns_equal_but_distinct_object() -> None:
    """copy() should return a new Todo with identical fields but different identity."""
    original = Todo(id=1, text="original task", done=False)

    copied = original.copy()

    # Should be equal in content
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at

    # But be a distinct object
    assert copied is not original


def test_copy_with_text_override() -> None:
    """copy(text='new') should return Todo with updated text field."""
    original = Todo(id=1, text="original task")
    original_updated_at = original.updated_at

    copied = original.copy(text="new task name")

    assert copied.text == "new task name"
    assert copied.id == original.id  # other fields unchanged
    assert copied.done == original.done
    assert copied.created_at == original.created_at

    # Original should be unchanged
    assert original.text == "original task"
    assert original.updated_at == original_updated_at


def test_copy_with_done_override() -> None:
    """copy(done=True) should return Todo with updated done field."""
    original = Todo(id=1, text="task", done=False)
    original_updated_at = original.updated_at

    copied = original.copy(done=True)

    assert copied.done is True
    assert copied.text == original.text  # other fields unchanged

    # Original should be unchanged
    assert original.done is False
    assert original.updated_at == original_updated_at


def test_copy_with_multiple_overrides() -> None:
    """copy() should accept multiple field overrides."""
    original = Todo(id=1, text="original", done=False)
    original_created = original.created_at
    original_updated = original.updated_at

    copied = original.copy(text="modified", done=True)

    assert copied.text == "modified"
    assert copied.done is True
    assert copied.id == original.id
    assert copied.created_at == original_created
    assert copied.updated_at == original_updated

    # Original completely unchanged
    assert original.text == "original"
    assert original.done is False


def test_original_unchanged_after_copy_with_modifications() -> None:
    """Original Todo should remain unchanged after any copy operation."""
    original = Todo(id=42, text="preserve me", done=False)
    original_created = original.created_at
    original_updated = original.updated_at

    # Perform copy with various overrides
    original.copy(text="changed")
    original.copy(done=True)
    original.copy(text="changed", done=True, id=99)

    # Original should be completely unchanged
    assert original.id == 42
    assert original.text == "preserve me"
    assert original.done is False
    assert original.created_at == original_created
    assert original.updated_at == original_updated
