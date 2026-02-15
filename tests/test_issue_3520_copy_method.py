"""Tests for Todo.copy() method - Issue #3520."""

from __future__ import annotations

from flywheel.todo import Todo


def test_copy_returns_independent_object() -> None:
    """todo.copy() should return a new independent Todo object."""
    original = Todo(id=1, text="original task", done=False)
    copy = original.copy()

    # Copy should be a Todo instance
    assert isinstance(copy, Todo)

    # Copy should have same field values
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at

    # Copy should be a different object
    assert copy is not original


def test_copy_with_kwargs_overrides_fields() -> None:
    """todo.copy(**kwargs) should allow overriding specific fields."""
    original = Todo(id=1, text="original task", done=False)
    copy = original.copy(text="new task", done=True)

    # Overridden fields should be updated
    assert copy.text == "new task"
    assert copy.done is True

    # Non-overridden fields should remain the same
    assert copy.id == original.id
    assert copy.created_at == original.created_at


def test_original_not_affected_by_copy_modifications() -> None:
    """Modifications to the copy should not affect the original."""
    original = Todo(id=1, text="original task", done=False)
    original_created_at = original.created_at

    copy = original.copy(text="modified", done=True)

    # Original should remain unchanged
    assert original.text == "original task"
    assert original.done is False
    assert original.created_at == original_created_at


def test_copy_modifications_do_not_affect_original() -> None:
    """Modifying the copy after creation should not affect the original."""
    original = Todo(id=1, text="original task", done=False)
    copy = original.copy()

    # Modify the copy
    copy.mark_done()
    copy.rename("modified copy")

    # Original should remain unchanged
    assert original.text == "original task"
    assert original.done is False
