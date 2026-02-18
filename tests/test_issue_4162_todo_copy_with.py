"""Tests for Todo.copy_with method (Issue #4162).

These tests verify that:
1. copy_with returns a new Todo instance
2. Original Todo remains unchanged after copy_with
3. Unspecified fields retain their original values
4. updated_at is automatically set to current time
5. Multiple fields can be updated at once
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_copy_with_returns_new_todo_with_updated_text() -> None:
    """copy_with should return a new Todo with updated text, original unchanged."""
    original = Todo(id=1, text="original text", done=False)
    original_updated_at = original.updated_at

    # Small delay to ensure new timestamp is different
    time.sleep(0.01)

    copy = original.copy_with(text="new text")

    # Copy should have new text
    assert copy.text == "new text"
    # Copy should have updated updated_at
    assert copy.updated_at > original_updated_at
    # Original should be unchanged
    assert original.text == "original text"
    assert original.updated_at == original_updated_at


def test_copy_with_returns_new_instance() -> None:
    """copy_with should return a new Todo instance, not the same object."""
    original = Todo(id=1, text="test")

    copy = original.copy_with(text="modified")

    assert copy is not original
    assert id(copy) != id(original)


def test_copy_with_multiple_fields() -> None:
    """copy_with should allow updating multiple fields at once."""
    original = Todo(id=1, text="original", done=False)
    original_created_at = original.created_at
    original_updated_at = original.updated_at

    time.sleep(0.01)

    copy = original.copy_with(text="new text", done=True)

    # Copy should have new values
    assert copy.text == "new text"
    assert copy.done is True
    assert copy.updated_at > original_updated_at
    # created_at should be preserved
    assert copy.created_at == original_created_at
    # Original should be unchanged
    assert original.text == "original"
    assert original.done is False


def test_copy_with_preserves_unspecified_fields() -> None:
    """copy_with should preserve all unspecified fields."""
    original = Todo(id=42, text="original", done=False)
    original_created_at = original.created_at

    time.sleep(0.01)

    copy = original.copy_with(done=True)

    # Only done should change
    assert copy.id == 42
    assert copy.text == "original"
    assert copy.done is True
    assert copy.created_at == original_created_at
    assert copy.updated_at > original.updated_at


def test_copy_with_no_args_returns_copy_with_updated_timestamp() -> None:
    """copy_with with no args should return a copy with only updated_at changed."""
    original = Todo(id=1, text="test", done=True)
    original_created_at = original.created_at
    original_updated_at = original.updated_at

    time.sleep(0.01)

    copy = original.copy_with()

    # All field values should be the same except updated_at
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original_created_at
    # But updated_at should be newer
    assert copy.updated_at > original_updated_at
    # And it should be a new instance
    assert copy is not original


def test_copy_with_can_update_all_fields() -> None:
    """copy_with should allow updating all mutable fields."""
    original = Todo(id=1, text="original", done=False)

    copy = original.copy_with(text="new text", done=True)

    assert copy.text == "new text"
    assert copy.done is True


def test_copy_with_strips_text_whitespace() -> None:
    """copy_with should strip whitespace from text like rename does."""
    original = Todo(id=1, text="original")

    copy = original.copy_with(text="  padded  ")

    assert copy.text == "padded"


def test_copy_with_rejects_empty_text() -> None:
    """copy_with should reject empty text after stripping."""
    original = Todo(id=1, text="original")

    # Empty string should raise ValueError
    try:
        original.copy_with(text="")
        raise AssertionError("Expected ValueError for empty text")
    except ValueError as e:
        assert "empty" in str(e).lower()
        # Original should be unchanged
        assert original.text == "original"


def test_copy_with_rejects_whitespace_only_text() -> None:
    """copy_with should reject whitespace-only text."""
    original = Todo(id=1, text="original")

    # Whitespace-only string should raise ValueError
    try:
        original.copy_with(text="   ")
        raise AssertionError("Expected ValueError for whitespace-only text")
    except ValueError as e:
        assert "empty" in str(e).lower()
        # Original should be unchanged
        assert original.text == "original"
