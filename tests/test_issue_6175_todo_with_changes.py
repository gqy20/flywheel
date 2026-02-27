"""Tests for Todo.with_changes method (Issue #6175).

These tests verify that:
1. with_changes returns a new Todo instance without modifying the original
2. The returned Todo has updated attributes
3. The returned Todo has updated_at set to current time
4. Calling with_changes() with no args returns a copy with same content
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_with_changes_done_true_returns_new_instance() -> None:
    """with_changes(done=True) should return a new Todo instance."""
    original = Todo(id=1, text="buy milk", done=False)
    original_updated_at = original.updated_at

    new_todo = original.with_changes(done=True)

    # Should be a different instance
    assert new_todo is not original
    # Original should remain unchanged
    assert original.done is False
    assert original.updated_at == original_updated_at


def test_with_changes_updates_attributes() -> None:
    """The returned Todo should have updated attribute values."""
    original = Todo(id=1, text="buy milk", done=False)

    new_todo = original.with_changes(done=True)

    assert new_todo.done is True
    # Other attributes should be preserved
    assert new_todo.id == original.id
    assert new_todo.text == original.text


def test_with_changes_updates_timestamp() -> None:
    """The returned Todo should have updated_at set to current time."""
    original = Todo(id=1, text="buy milk", done=False)
    original_updated_at = original.updated_at

    new_todo = original.with_changes(done=True)

    # updated_at should be different (newer)
    assert new_todo.updated_at != original_updated_at


def test_with_changes_text_parameter() -> None:
    """with_changes(text=...) should update the text field."""
    original = Todo(id=1, text="old text", done=False)

    new_todo = original.with_changes(text="new text")

    assert new_todo.text == "new text"
    # Original unchanged
    assert original.text == "old text"


def test_with_changes_multiple_parameters() -> None:
    """with_changes should accept multiple parameters."""
    original = Todo(id=1, text="old text", done=False)

    new_todo = original.with_changes(text="new text", done=True)

    assert new_todo.text == "new text"
    assert new_todo.done is True


def test_with_changes_no_args_returns_copy() -> None:
    """with_changes() with no args should return a copy with same content."""
    original = Todo(id=1, text="buy milk", done=True)

    copy_todo = original.with_changes()

    # Should be a different instance
    assert copy_todo is not original
    # Should have same content (except updated_at)
    assert copy_todo.id == original.id
    assert copy_todo.text == original.text
    assert copy_todo.done == original.done
    # created_at should be preserved
    assert copy_todo.created_at == original.created_at
    # updated_at should be updated
    assert copy_todo.updated_at != original.updated_at


def test_with_changes_preserves_created_at() -> None:
    """with_changes should preserve the original created_at timestamp."""
    original = Todo(id=1, text="buy milk", done=False)
    original_created_at = original.created_at

    new_todo = original.with_changes(done=True)

    assert new_todo.created_at == original_created_at
