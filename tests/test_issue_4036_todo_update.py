"""Tests for Todo.update() method (Issue #4036).

These tests verify that:
1. update(text='new') only updates text
2. update(done=True) only updates done status
3. update(text='new', done=True) updates both fields
4. update() with no arguments does not modify any field
5. update() only updates updated_at once when multiple fields change
6. update(text='') raises ValueError (consistent with rename behavior)
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_update_text_only() -> None:
    """update(text='new') should only update the text field."""
    todo = Todo(id=1, text="old text", done=False)
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp would change if updated
    time.sleep(0.01)

    todo.update(text="new text")

    assert todo.text == "new text"
    assert todo.done is False  # Should remain unchanged
    assert todo.updated_at != original_updated_at  # Should be updated


def test_update_done_only() -> None:
    """update(done=True) should only update the done field."""
    todo = Todo(id=1, text="task", done=False)
    original_updated_at = todo.updated_at

    time.sleep(0.01)

    todo.update(done=True)

    assert todo.done is True
    assert todo.text == "task"  # Should remain unchanged
    assert todo.updated_at != original_updated_at  # Should be updated


def test_update_both_fields() -> None:
    """update(text='new', done=True) should update both fields and updated_at once."""
    todo = Todo(id=1, text="old text", done=False)
    original_updated_at = todo.updated_at

    time.sleep(0.01)

    todo.update(text="new text", done=True)

    assert todo.text == "new text"
    assert todo.done is True
    assert todo.updated_at != original_updated_at  # Should be updated


def test_update_no_arguments() -> None:
    """update() with no arguments should not modify any field or updated_at."""
    todo = Todo(id=1, text="task", done=False)
    original_text = todo.text
    original_done = todo.done
    original_updated_at = todo.updated_at

    todo.update()

    assert todo.text == original_text
    assert todo.done == original_done
    assert todo.updated_at == original_updated_at  # Should NOT be updated


def test_update_empty_text_raises_error() -> None:
    """update(text='') should raise ValueError (consistent with rename behavior)."""
    todo = Todo(id=1, text="task", done=False)

    try:
        todo.update(text="")
        raise AssertionError("Expected ValueError for empty text")
    except ValueError as e:
        assert "empty" in str(e).lower()


def test_update_whitespace_text_raises_error() -> None:
    """update(text='  ') should raise ValueError after stripping."""
    todo = Todo(id=1, text="task", done=False)

    try:
        todo.update(text="   ")
        raise AssertionError("Expected ValueError for whitespace-only text")
    except ValueError as e:
        assert "empty" in str(e).lower()


def test_update_strips_text() -> None:
    """update(text='  trimmed  ') should strip whitespace like rename."""
    todo = Todo(id=1, text="task", done=False)

    todo.update(text="  trimmed text  ")

    assert todo.text == "trimmed text"


def test_update_done_false() -> None:
    """update(done=False) should set done to False."""
    todo = Todo(id=1, text="task", done=True)

    todo.update(done=False)

    assert todo.done is False


def test_update_same_values_still_updates_timestamp() -> None:
    """update() should update updated_at even if values are the same.

    This is consistent with mark_done() behavior which updates even if already done.
    """
    todo = Todo(id=1, text="task", done=False)
    original_updated_at = todo.updated_at

    time.sleep(0.01)

    # Update with same values - should still update timestamp per issue requirements
    todo.update(text="task", done=False)

    # updated_at should change because we explicitly called update
    assert todo.updated_at != original_updated_at


def test_update_text_none_does_not_change_text() -> None:
    """update(done=True) with text=None should not change text."""
    todo = Todo(id=1, text="original text", done=False)
    original_text = todo.text

    todo.update(done=True)

    assert todo.text == original_text


def test_update_done_none_does_not_change_done() -> None:
    """update(text='new') with done=None should not change done."""
    todo = Todo(id=1, text="task", done=True)
    original_done = todo.done

    todo.update(text="new task")

    assert todo.done == original_done
