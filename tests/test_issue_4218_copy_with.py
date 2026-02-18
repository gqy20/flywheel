"""Tests for issue #4218: Todo.copy_with() immutable update method."""

from __future__ import annotations

import time

import pytest

from flywheel.todo import Todo


def test_copy_with_updates_done_field() -> None:
    """copy_with(done=True) should return new Todo with done=True."""
    original = Todo(id=1, text="test")
    original_updated_at = original.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    new_todo = original.copy_with(done=True)

    # New instance should have done=True
    assert new_todo.done is True
    # New instance should have updated updated_at
    assert new_todo.updated_at > original_updated_at
    # Should be a different object
    assert new_todo is not original


def test_copy_with_preserves_original() -> None:
    """Original Todo should remain unchanged after copy_with."""
    original = Todo(id=1, text="original text", done=False)
    original_done = original.done
    original_text = original.text
    original_updated_at = original.updated_at

    original.copy_with(done=True, text="new text")

    # Original should be unchanged
    assert original.done == original_done
    assert original.text == original_text
    assert original.updated_at == original_updated_at


def test_copy_with_updates_text_field() -> None:
    """copy_with(text='new') should return new Todo with updated text."""
    original = Todo(id=1, text="old text")

    new_todo = original.copy_with(text="new text")

    assert new_todo.text == "new text"
    assert original.text == "old text"


def test_copy_with_strips_text_whitespace() -> None:
    """copy_with should strip whitespace from text, matching rename() behavior."""
    original = Todo(id=1, text="original")

    new_todo = original.copy_with(text="  padded  ")

    assert new_todo.text == "padded"


def test_copy_with_rejects_empty_text() -> None:
    """copy_with should reject empty text, matching rename() behavior."""
    original = Todo(id=1, text="original")
    original_updated_at = original.updated_at

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        original.copy_with(text="")

    # Verify original unchanged after failed validation
    assert original.text == "original"
    assert original.updated_at == original_updated_at


def test_copy_with_rejects_whitespace_only_text() -> None:
    """copy_with should reject whitespace-only text."""
    original = Todo(id=1, text="original")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        original.copy_with(text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        original.copy_with(text="\t\n")


def test_copy_with_no_changes_returns_equivalent_todo() -> None:
    """copy_with() with no args should return new Todo with same values."""
    original = Todo(id=1, text="test", done=True)

    time.sleep(0.01)
    new_todo = original.copy_with()

    # Values should be same
    assert new_todo.id == original.id
    assert new_todo.text == original.text
    assert new_todo.done == original.done
    assert new_todo.created_at == original.created_at
    # But updated_at should be refreshed
    assert new_todo.updated_at >= original.updated_at
    # And it should be a different object
    assert new_todo is not original


def test_copy_with_can_update_id() -> None:
    """copy_with should allow updating id field."""
    original = Todo(id=1, text="test")

    new_todo = original.copy_with(id=99)

    assert new_todo.id == 99
    assert original.id == 1
