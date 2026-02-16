"""Tests for issue #3666: update_text() method alias for rename()."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_update_text_behaves_identically_to_rename() -> None:
    """Issue #3666: update_text() should behave identically to rename()."""
    todo = Todo(id=1, text="original")

    # Both methods should update text field
    todo.update_text("new text")
    assert todo.text == "new text"


def test_update_text_updates_timestamp() -> None:
    """Issue #3666: update_text() should update updated_at timestamp."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    todo.update_text("new text")
    assert todo.updated_at >= original_updated_at


def test_update_text_rejects_empty_string() -> None:
    """Issue #3666: update_text() should reject empty strings (same as rename())."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.update_text("")

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_update_text_rejects_whitespace_only() -> None:
    """Issue #3666: update_text() should reject whitespace-only strings."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.update_text("   ")

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_update_text_strips_whitespace() -> None:
    """Issue #3666: update_text() should strip whitespace (same as rename())."""
    todo = Todo(id=1, text="original")

    todo.update_text("  padded  ")
    assert todo.text == "padded"
