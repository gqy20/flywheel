"""Tests for Todo.copy() method - immutable-style updates.

Issue #5889: Add copy/clone method to Todo for immutable-style updates
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_copy_returns_new_instance() -> None:
    """copy() should return a new Todo instance, not the same object."""
    original = Todo(id=1, text="test")
    copy = original.copy()

    assert copy is not original
    assert isinstance(copy, Todo)


def test_todo_copy_preserves_all_fields() -> None:
    """copy() without arguments should return a Todo with identical fields."""
    original = Todo(id=1, text="test", done=True)
    original.created_at = "2024-01-01T00:00:00+00:00"
    original.updated_at = "2024-01-02T00:00:00+00:00"

    copy = original.copy()

    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_todo_copy_with_updates() -> None:
    """copy(with_updates) should override specified fields."""
    original = Todo(id=1, text="original", done=False)
    original.created_at = "2024-01-01T00:00:00+00:00"
    original.updated_at = "2024-01-02T00:00:00+00:00"

    copy = original.copy({"done": True})

    assert copy.done is True
    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_todo_copy_original_unchanged() -> None:
    """Original Todo should be unchanged after copy operation."""
    original = Todo(id=1, text="original", done=False)
    original_updated_at = original.updated_at

    copy = original.copy({"done": True, "text": "modified"})

    assert original.done is False
    assert original.text == "original"
    assert original.updated_at == original_updated_at
    assert copy.done is True
    assert copy.text == "modified"


def test_todo_copy_supports_all_field_overrides() -> None:
    """copy() should allow overriding any field."""
    original = Todo(id=1, text="original")

    copy = original.copy({
        "id": 99,
        "text": "new text",
        "done": True,
        "created_at": "2023-01-01T00:00:00+00:00",
        "updated_at": "2023-12-31T23:59:59+00:00",
    })

    assert copy.id == 99
    assert copy.text == "new text"
    assert copy.done is True
    assert copy.created_at == "2023-01-01T00:00:00+00:00"
    assert copy.updated_at == "2023-12-31T23:59:59+00:00"


def test_todo_copy_empty_dict_same_as_no_args() -> None:
    """copy({}) should behave the same as copy()."""
    original = Todo(id=1, text="test", done=True)

    copy_empty = original.copy({})
    copy_no_args = original.copy()

    assert copy_empty.id == copy_no_args.id
    assert copy_empty.text == copy_no_args.text
    assert copy_empty.done == copy_no_args.done
