"""Tests for Todo.copy() method (Issue #5889).

These tests verify that:
1. todo.copy() returns a new Todo with identical fields
2. todo.copy({'done': True}) returns new Todo with done=True
3. Original Todo is unchanged after copy operation
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_new_instance() -> None:
    """copy() should return a new Todo instance, not the same object."""
    original = Todo(id=1, text="buy milk")
    copy = original.copy()

    assert copy is not original
    assert isinstance(copy, Todo)


def test_todo_copy_preserves_all_fields() -> None:
    """copy() should return a Todo with identical fields."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy()

    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_todo_copy_with_updates_overrides_fields() -> None:
    """copy({'done': True}) should return new Todo with specified overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy({"done": True})

    assert copy.done is True
    assert original.done is False  # original unchanged


def test_todo_copy_with_multiple_updates() -> None:
    """copy() should handle multiple field overrides."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy({"text": "buy bread", "done": True})

    assert copy.text == "buy bread"
    assert copy.done is True
    assert copy.id == original.id  # id unchanged
    assert original.text == "buy milk"  # original unchanged
    assert original.done is False


def test_todo_copy_original_unchanged() -> None:
    """Original Todo should be unchanged after copy operation."""
    original = Todo(id=1, text="original text", done=False)
    original_created = original.created_at
    original_updated = original.updated_at

    copy = original.copy({"text": "new text", "done": True})

    # Verify original is unchanged
    assert original.text == "original text"
    assert original.done is False
    assert original.created_at == original_created
    assert original.updated_at == original_updated

    # Verify copy has new values
    assert copy.text == "new text"
    assert copy.done is True


def test_todo_copy_empty_dict() -> None:
    """copy({}) should behave like copy() with no args."""
    original = Todo(id=1, text="buy milk")
    copy = original.copy({})

    assert copy is not original
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done


def test_todo_copy_no_args() -> None:
    """copy() with no arguments should create exact clone."""
    original = Todo(id=42, text="task", done=True)
    copy = original.copy()

    assert copy is not original
    assert copy.id == 42
    assert copy.text == "task"
    assert copy.done is True


def test_todo_copy_can_override_id() -> None:
    """copy() should allow overriding id field."""
    original = Todo(id=1, text="buy milk")
    copy = original.copy({"id": 2})

    assert copy.id == 2
    assert original.id == 1  # original unchanged


def test_todo_copy_can_override_timestamps() -> None:
    """copy() should allow overriding timestamp fields."""
    original = Todo(id=1, text="buy milk")
    new_time = "2024-01-01T00:00:00+00:00"
    copy = original.copy({"created_at": new_time, "updated_at": new_time})

    assert copy.created_at == new_time
    assert copy.updated_at == new_time
