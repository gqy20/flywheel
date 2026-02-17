"""Tests for Todo.update() method (Issue #4036).

These tests verify that:
1. update() can update multiple attributes in a single call
2. update() updates the updated_at timestamp
3. update() validates text is not empty when text is updated
4. update() only updates provided attributes
5. update() rejects unknown attributes
"""

from __future__ import annotations

import time

import pytest

from flywheel.todo import Todo


def test_todo_update_single_attribute_text() -> None:
    """update() should update text attribute."""
    todo = Todo(id=1, text="original text", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp changes
    time.sleep(0.01)

    todo.update(text="new text")

    assert todo.text == "new text"
    assert todo.updated_at > original_updated_at


def test_todo_update_single_attribute_done() -> None:
    """update() should update done attribute."""
    todo = Todo(id=1, text="task", done=False)
    original_updated_at = todo.updated_at

    time.sleep(0.01)

    todo.update(done=True)

    assert todo.done is True
    assert todo.updated_at > original_updated_at


def test_todo_update_multiple_attributes() -> None:
    """update() should update multiple attributes at once."""
    todo = Todo(id=1, text="original", done=False)
    original_updated_at = todo.updated_at

    time.sleep(0.01)

    todo.update(text="updated", done=True)

    assert todo.text == "updated"
    assert todo.done is True
    assert todo.updated_at > original_updated_at


def test_todo_update_strips_whitespace_from_text() -> None:
    """update() should strip whitespace from text like rename()."""
    todo = Todo(id=1, text="original")

    todo.update(text="  trimmed text  ")

    assert todo.text == "trimmed text"


def test_todo_update_empty_text_raises_error() -> None:
    """update() should raise ValueError for empty text like rename()."""
    todo = Todo(id=1, text="original")

    with pytest.raises(ValueError, match="cannot be empty"):
        todo.update(text="   ")


def test_todo_update_only_provided_attributes() -> None:
    """update() should only update attributes that are provided."""
    todo = Todo(id=1, text="original", done=False)

    todo.update(done=True)  # Only update done, not text

    assert todo.text == "original"  # text should remain unchanged
    assert todo.done is True


def test_todo_update_unknown_attribute_raises_error() -> None:
    """update() should reject unknown attributes."""
    todo = Todo(id=1, text="task")

    with pytest.raises(ValueError, match="Unknown attribute"):
        todo.update(unknown_attr="value")


def test_todo_update_no_arguments_still_updates_timestamp() -> None:
    """update() with no arguments should still update timestamp."""
    todo = Todo(id=1, text="task")
    original_updated_at = todo.updated_at

    time.sleep(0.01)

    todo.update()

    assert todo.updated_at > original_updated_at


def test_todo_update_id_is_not_modifiable() -> None:
    """update() should not allow modifying the id attribute."""
    todo = Todo(id=1, text="task")

    with pytest.raises(ValueError, match="id"):
        todo.update(id=999)
