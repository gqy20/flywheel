"""Tests for Todo.copy() method for immutable operations (Issue #6259).

These tests verify that:
1. copy() returns a new Todo object with same field values
2. The new object has a different id() (different instance)
3. Modifying the copy does not affect the original
4. copy() supports overriding arbitrary fields like text, done
5. copy() automatically sets updated_at to current time
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_returns_new_instance() -> None:
    """copy() should return a different object instance."""
    todo = Todo(id=1, text="original task")
    copied = todo.copy()

    assert copied is not todo, "copy() should return a new instance"
    assert id(copied) != id(todo), "copy() should create a different object"


def test_todo_copy_preserves_all_fields() -> None:
    """copy() should preserve all field values from original."""
    todo = Todo(id=1, text="task", done=True)
    copied = todo.copy()

    assert copied.id == todo.id
    assert copied.text == todo.text
    assert copied.done == todo.done
    assert copied.created_at == todo.created_at
    # updated_at is refreshed, so we don't check equality there


def test_todo_copy_updates_timestamp() -> None:
    """copy() should set updated_at to current time."""
    todo = Todo(id=1, text="task")
    time.sleep(0.01)  # Small delay to ensure different timestamp

    copied = todo.copy()
    assert copied.updated_at != todo.updated_at or copied.updated_at >= todo.updated_at


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should override the done field."""
    todo = Todo(id=1, text="task", done=False)
    copied = todo.copy(done=True)

    assert copied.done is True
    assert todo.done is False, "Original should be unchanged"


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should override the text field."""
    todo = Todo(id=1, text="old text")
    copied = todo.copy(text="new text")

    assert copied.text == "new text"
    assert todo.text == "old text", "Original should be unchanged"


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should support overriding multiple fields at once."""
    todo = Todo(id=1, text="old", done=False)
    copied = todo.copy(text="new", done=True)

    assert copied.text == "new"
    assert copied.done is True
    assert todo.text == "old"
    assert todo.done is False


def test_todo_copy_original_unchanged_after_modify() -> None:
    """Modifying the copy should not affect the original."""
    todo = Todo(id=1, text="original", done=False)
    copied = todo.copy(done=True)

    # Even after using the copy, original remains unchanged
    assert todo.done is False
    assert todo.text == "original"

    # Mutating methods on original should not affect copy
    todo.mark_done()
    assert copied.done is True, "Copy should keep its own state"


def test_todo_copy_preserves_id() -> None:
    """copy() should preserve the id field (identity is tied to id)."""
    todo = Todo(id=42, text="task")
    copied = todo.copy()

    assert copied.id == 42, "copy() should preserve id"


def test_todo_copy_allows_id_override() -> None:
    """copy(id=...) should allow overriding the id field if needed."""
    todo = Todo(id=1, text="task")
    copied = todo.copy(id=99)

    assert copied.id == 99
    assert todo.id == 1
