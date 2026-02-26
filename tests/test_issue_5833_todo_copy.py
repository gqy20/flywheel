"""Tests for Todo.copy() method (Issue #5833).

These tests verify that:
1. todo.copy() returns a different object instance with same fields
2. todo.copy(text='new') returns a new object with text overridden
3. Modifying the copy does not affect the original object
4. copy() preserves all fields by default (id, text, done, created_at, updated_at)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_different_object() -> None:
    """copy() should return a new object instance, not the same object."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    assert copied is not original, "copy() should return a different object"
    assert isinstance(copied, Todo)


def test_todo_copy_preserves_all_fields() -> None:
    """copy() should preserve all fields from the original todo."""
    original = Todo(id=1, text="buy milk", done=True)
    copied = original.copy()

    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should return a todo with only text changed."""
    original = Todo(id=1, text="buy milk", done=True)
    copied = original.copy(text="buy bread")

    assert copied.text == "buy bread"
    # Other fields should remain the same
    assert copied.id == original.id
    assert copied.done == original.done


def test_todo_copy_with_id_override() -> None:
    """copy(id=2) should return a todo with only id changed."""
    original = Todo(id=1, text="buy milk", done=True)
    copied = original.copy(id=2)

    assert copied.id == 2
    # Other fields should remain the same
    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_with_done_override() -> None:
    """copy(done=False) should return a todo with only done changed."""
    original = Todo(id=1, text="buy milk", done=True)
    copied = original.copy(done=False)

    assert copied.done is False
    # Other fields should remain the same
    assert copied.id == original.id
    assert copied.text == original.text


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should allow overriding multiple fields at once."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(id=2, text="buy bread", done=True)

    assert copied.id == 2
    assert copied.text == "buy bread"
    assert copied.done is True


def test_todo_copy_independence() -> None:
    """Modifying a copy should not affect the original object."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Modify the copy
    copied.text = "modified text"
    copied.done = True

    # Original should remain unchanged
    assert original.text == "buy milk"
    assert original.done is False


def test_todo_copy_preserves_timestamps() -> None:
    """copy() should preserve created_at and updated_at timestamps."""
    original = Todo(id=1, text="buy milk", done=False)
    original_timestamp = original.created_at

    copied = original.copy()

    assert copied.created_at == original_timestamp
    assert copied.updated_at == original.updated_at


def test_todo_copy_with_created_at_override() -> None:
    """copy(created_at='...') should allow overriding created_at."""
    original = Todo(id=1, text="buy milk", done=False)
    new_timestamp = "2025-01-01T00:00:00+00:00"
    copied = original.copy(created_at=new_timestamp)

    assert copied.created_at == new_timestamp
    assert copied.id == original.id
    assert copied.text == original.text
