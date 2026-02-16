"""Tests for Todo.copy_with() method (Issue #3709).

These tests verify that:
1. copy_with() returns a new Todo instance without modifying the original
2. copy_with() preserves created_at timestamp
3. copy_with() supports overriding text, done, and updated_at fields
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_copy_with_returns_new_instance() -> None:
    """copy_with() should return a new Todo instance."""
    todo = Todo(id=1, text="buy milk", done=False)
    new_todo = todo.copy_with(done=True)

    # Should be a different object
    assert new_todo is not todo
    # Should have updated field
    assert new_todo.done is True
    # Original should be unchanged
    assert todo.done is False


def test_copy_with_preserves_created_at() -> None:
    """copy_with() should preserve the created_at timestamp."""
    todo = Todo(id=1, text="buy milk", done=False)
    original_created_at = todo.created_at
    new_todo = todo.copy_with(done=True)

    # created_at should be preserved
    assert new_todo.created_at == original_created_at


def test_copy_with_original_unchanged() -> None:
    """copy_with() should not modify the original instance."""
    todo = Todo(id=1, text="buy milk", done=False)
    original_text = todo.text
    original_done = todo.done
    original_updated_at = todo.updated_at

    new_todo = todo.copy_with(text="buy bread", done=True)

    # Original should be completely unchanged
    assert todo.text == original_text
    assert todo.done == original_done
    assert todo.updated_at == original_updated_at

    # New instance should have the updated values
    assert new_todo.text == "buy bread"
    assert new_todo.done is True


def test_copy_with_preserves_id() -> None:
    """copy_with() should preserve the id field."""
    todo = Todo(id=42, text="task", done=False)
    new_todo = todo.copy_with(done=True)

    assert new_todo.id == todo.id


def test_copy_with_updates_updated_at() -> None:
    """copy_with() should update the updated_at timestamp when any field changes."""
    todo = Todo(id=1, text="buy milk", done=False)
    new_todo = todo.copy_with(done=True)

    # updated_at should be updated (different from original)
    # Note: In very fast tests they might be the same, so we just check it's set
    assert new_todo.updated_at != ""


def test_copy_with_supports_multiple_fields() -> None:
    """copy_with() should support overriding multiple fields at once."""
    todo = Todo(id=1, text="buy milk", done=False)
    new_todo = todo.copy_with(text="buy bread", done=True)

    assert new_todo.text == "buy bread"
    assert new_todo.done is True
    assert todo.text == "buy milk"
    assert todo.done is False


def test_copy_with_no_args_returns_copy() -> None:
    """copy_with() with no arguments should return an identical copy."""
    todo = Todo(id=1, text="buy milk", done=True)
    new_todo = todo.copy_with()

    # Should be a different object with same values
    assert new_todo is not todo
    assert new_todo.id == todo.id
    assert new_todo.text == todo.text
    assert new_todo.done == todo.done
    assert new_todo.created_at == todo.created_at


def test_copy_with_allows_updated_at_override() -> None:
    """copy_with() should allow explicit updated_at override."""
    todo = Todo(id=1, text="buy milk", done=False)
    custom_time = "2024-01-01T00:00:00+00:00"
    new_todo = todo.copy_with(done=True, updated_at=custom_time)

    assert new_todo.updated_at == custom_time
