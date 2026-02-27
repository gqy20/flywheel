"""Tests for Todo.with_changes() method (Issue #6175).

These tests verify that:
1. with_changes() returns a new Todo instance, leaving original unchanged
2. with_changes(done=True) updates the done field
3. with_changes(text="new") updates the text field
4. with_changes() with no args returns a copy with new updated_at
5. Empty text raises ValueError (consistent with rename())
6. created_at is preserved from original
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_with_changes_returns_new_instance() -> None:
    """with_changes() should return a new Todo instance."""
    original = Todo(id=1, text="original task", done=False)
    copy = original.with_changes(done=True)

    # Should be different objects
    assert copy is not original
    # Original should be unchanged
    assert original.done is False
    assert original.text == "original task"


def test_with_changes_done_true() -> None:
    """with_changes(done=True) should set done=True in new instance."""
    original = Todo(id=1, text="task", done=False)
    updated = original.with_changes(done=True)

    assert updated.done is True
    assert updated.id == original.id
    assert updated.text == original.text
    assert updated.created_at == original.created_at


def test_with_changes_done_false() -> None:
    """with_changes(done=False) should set done=False in new instance."""
    original = Todo(id=1, text="task", done=True)
    updated = original.with_changes(done=False)

    assert updated.done is False
    assert original.done is True  # Original unchanged


def test_with_changes_text() -> None:
    """with_changes(text="new") should update text in new instance."""
    original = Todo(id=1, text="old text", done=False)
    updated = original.with_changes(text="new text")

    assert updated.text == "new text"
    assert original.text == "old text"  # Original unchanged


def test_with_changes_text_stripped() -> None:
    """with_changes(text) should strip whitespace like rename()."""
    original = Todo(id=1, text="task", done=False)
    updated = original.with_changes(text="  padded text  ")

    assert updated.text == "padded text"


def test_with_changes_empty_text_raises() -> None:
    """with_changes(text="") should raise ValueError like rename()."""
    import pytest

    original = Todo(id=1, text="task", done=False)

    with pytest.raises(ValueError, match="empty"):
        original.with_changes(text="")


def test_with_changes_whitespace_only_text_raises() -> None:
    """with_changes(text="   ") should raise ValueError after stripping."""
    import pytest

    original = Todo(id=1, text="task", done=False)

    with pytest.raises(ValueError, match="empty"):
        original.with_changes(text="   ")


def test_with_changes_no_args_returns_copy() -> None:
    """with_changes() with no args should return a copy with same values."""
    original = Todo(id=1, text="task", done=True)
    copy = original.with_changes()

    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy is not original


def test_with_changes_updates_updated_at() -> None:
    """with_changes() should set updated_at to current time."""
    original = Todo(id=1, text="task", done=False)
    original_updated_at = original.updated_at

    # Small delay to ensure time difference
    time.sleep(0.01)

    updated = original.with_changes(done=True)

    # updated_at should be different (newer)
    assert updated.updated_at != original_updated_at
    # Original's updated_at should be unchanged
    assert original.updated_at == original_updated_at


def test_with_changes_preserves_created_at() -> None:
    """with_changes() should preserve created_at from original."""
    original = Todo(id=1, text="task", done=False)
    time.sleep(0.01)  # Small delay

    updated = original.with_changes(done=True)

    # created_at should be exactly the same
    assert updated.created_at == original.created_at


def test_with_changes_multiple_fields() -> None:
    """with_changes() should support updating multiple fields at once."""
    original = Todo(id=1, text="old", done=False)
    updated = original.with_changes(text="new", done=True)

    assert updated.text == "new"
    assert updated.done is True
    assert original.text == "old"
    assert original.done is False


def test_with_changes_id_preserved() -> None:
    """with_changes() should preserve id from original."""
    original = Todo(id=42, text="task", done=False)
    updated = original.with_changes(done=True)

    assert updated.id == 42
