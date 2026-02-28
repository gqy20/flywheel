"""Tests for Todo.copy() method (Issue #6383).

These tests verify that:
1. copy() returns a new Todo object with same content
2. copy(text='new') modifies only the text field
3. copy(done=True) modifies only the done field
4. Timestamps are preserved unless explicitly overridden
5. Original todo is not modified after copy
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_copy_returns_new_object() -> None:
    """todo.copy() should return a new Todo object with different identity."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    # Should be different objects
    assert copy is not original
    # Should have same values
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done


def test_copy_preserves_all_fields() -> None:
    """todo.copy() should preserve all field values including timestamps."""
    original = Todo(id=42, text="test task", done=True)
    copy = original.copy()

    assert copy.id == 42
    assert copy.text == "test task"
    assert copy.done is True
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_copy_with_text_override() -> None:
    """todo.copy(text='new') should return copy with modified text only."""
    original = Todo(id=1, text="old text", done=False)
    copy = original.copy(text="new text")

    # Text should be changed
    assert copy.text == "new text"
    # Other fields preserved
    assert copy.id == 1
    assert copy.done is False


def test_copy_with_done_override() -> None:
    """todo.copy(done=True) should return copy with modified done only."""
    original = Todo(id=1, text="task", done=False)
    copy = original.copy(done=True)

    # Done should be changed
    assert copy.done is True
    # Other fields preserved
    assert copy.id == 1
    assert copy.text == "task"


def test_copy_preserves_timestamps() -> None:
    """copy() should preserve created_at/updated_at unless explicitly overridden."""
    original = Todo(id=1, text="task", done=False)
    original_timestamp = original.created_at
    original_updated = original.updated_at

    copy = original.copy(text="modified")

    # Timestamps should be preserved in copy
    assert copy.created_at == original_timestamp
    assert copy.updated_at == original_updated


def test_copy_does_not_modify_original() -> None:
    """Original todo should remain unchanged after copy with overrides."""
    original = Todo(id=1, text="original text", done=False)
    original_text = original.text
    original_done = original.done

    # Create copy with overrides
    _copy = original.copy(text="new text", done=True)

    # Original should be unchanged
    assert original.text == original_text
    assert original.done == original_done


def test_copy_with_multiple_overrides() -> None:
    """todo.copy() should support multiple field overrides at once."""
    original = Todo(id=1, text="old", done=False)
    copy = original.copy(text="new", done=True)

    assert copy.text == "new"
    assert copy.done is True
    assert copy.id == 1  # unchanged


def test_copy_with_id_override() -> None:
    """todo.copy() should allow overriding id for creating new todos."""
    original = Todo(id=1, text="template", done=False)
    copy = original.copy(id=2)

    assert copy.id == 2
    assert copy.text == "template"
