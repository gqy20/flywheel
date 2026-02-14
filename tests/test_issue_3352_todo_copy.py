"""Tests for Todo.copy method (Issue #3352).

These tests verify that:
1. todo.copy() returns a new Todo object with identical values
2. todo.copy(**overrides) allows selective field overrides
3. The copy is a distinct object (not the same instance)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_new_object_with_same_values() -> None:
    """copy() should return a new Todo with identical values."""
    original = Todo(id=1, text="a")
    copy = original.copy()

    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at

    # Verify it's a different object
    assert copy is not original


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should return a copy with only text changed."""
    original = Todo(id=1, text="a")
    copy = original.copy(text="b")

    assert copy.id == original.id
    assert copy.text == "b"
    assert copy.done == original.done


def test_todo_copy_with_id_override() -> None:
    """copy() should allow overriding id."""
    original = Todo(id=1, text="task")
    copy = original.copy(id=2)

    assert copy.id == 2
    assert copy.text == original.text


def test_todo_copy_with_done_override() -> None:
    """copy() should allow overriding done status."""
    original = Todo(id=1, text="task", done=False)
    copy = original.copy(done=True)

    assert copy.done is True
    assert original.done is False  # Original unchanged


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should allow multiple field overrides."""
    original = Todo(id=1, text="old", done=False)
    copy = original.copy(id=2, text="new", done=True)

    assert copy.id == 2
    assert copy.text == "new"
    assert copy.done is True


def test_todo_copy_preserves_timestamps() -> None:
    """copy() should preserve timestamps unless explicitly overridden."""
    original = Todo(id=1, text="task")
    original_ts = original.created_at
    copy = original.copy()

    assert copy.created_at == original_ts
    assert copy.updated_at == original_ts


def test_todo_copy_does_not_modify_original() -> None:
    """copy() should not affect the original Todo."""
    original = Todo(id=1, text="original", done=False)
    original_id = original.id
    original_text = original.text
    original_done = original.done

    _ = original.copy(id=99, text="modified", done=True)

    # Original should remain unchanged
    assert original.id == original_id
    assert original.text == original_text
    assert original.done == original_done


def test_todo_copy_with_done_todo() -> None:
    """copy() should work correctly on already-done todos."""
    original = Todo(id=1, text="completed", done=True)
    copy = original.copy()

    assert copy.done is True
    assert copy.text == "completed"
