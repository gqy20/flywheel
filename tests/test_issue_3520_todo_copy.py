"""Tests for Todo.copy method (Issue #3520).

These tests verify that:
1. todo.copy() returns a new independent Todo object with all fields copied
2. todo.copy(**kwargs) can override specific fields
3. Modifications to the copy don't affect the original object
4. created_at timestamp is preserved in the copy
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_independent_object() -> None:
    """copy() should return a new Todo object that is independent of original."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    # Should be a different object
    assert copy is not original
    # Should have same field values
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should return a copy with updated text field."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(text="buy bread")

    # Original should be unchanged
    assert original.text == "buy milk"
    # Copy should have new text
    assert copy.text == "buy bread"
    # Other fields should be same
    assert copy.id == original.id
    assert copy.done == original.done


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should return a copy with updated done field."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(done=True)

    # Original should be unchanged
    assert original.done is False
    # Copy should have done=True
    assert copy.done is True


def test_todo_copy_with_multiple_overrides() -> None:
    """copy(id=2, text='new', done=True) should override multiple fields."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(id=2, text="buy bread", done=True)

    # Original should be unchanged
    assert original.id == 1
    assert original.text == "buy milk"
    assert original.done is False

    # Copy should have all new values
    assert copy.id == 2
    assert copy.text == "buy bread"
    assert copy.done is True


def test_todo_copy_preserves_created_at() -> None:
    """copy() should preserve created_at timestamp from original."""
    original = Todo(id=1, text="buy milk")
    original_created_at = original.created_at

    copy = original.copy()

    # created_at should be preserved
    assert copy.created_at == original_created_at


def test_todo_copy_modifications_dont_affect_original() -> None:
    """Modifications to copy should not affect original object."""
    original = Todo(id=1, text="buy milk", done=False)

    copy = original.copy()
    copy.mark_done()

    # Original should still be undone
    assert original.done is False
    # Copy should be done
    assert copy.done is True

    # Modify copy text
    copy.rename("new text")
    assert original.text == "buy milk"
    assert copy.text == "new text"


def test_todo_copy_with_empty_kwargs() -> None:
    """copy() with no kwargs should work like copy()."""
    original = Todo(id=1, text="buy milk", done=False)
    copy1 = original.copy()
    copy2 = original.copy()

    # Both copies should be independent
    assert copy1 is not copy2
    assert copy1 is not original
    assert copy2 is not original

    # All should have same field values
    assert copy1.text == original.text
    assert copy2.text == original.text


def test_todo_copy_can_override_all_fields() -> None:
    """copy() should allow overriding all fields including timestamps."""
    original = Todo(id=1, text="original", done=False)
    new_created_at = "2024-01-01T00:00:00+00:00"
    new_updated_at = "2024-01-02T00:00:00+00:00"

    copy = original.copy(
        id=2, text="copy", done=True, created_at=new_created_at, updated_at=new_updated_at
    )

    # Copy should have all new values
    assert copy.id == 2
    assert copy.text == "copy"
    assert copy.done is True
    assert copy.created_at == new_created_at
    assert copy.updated_at == new_updated_at

    # Original should be unchanged
    assert original.id == 1
    assert original.text == "original"
    assert original.done is False
