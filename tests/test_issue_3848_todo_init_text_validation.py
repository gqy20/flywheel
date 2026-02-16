"""Tests for Todo.__init__ text validation (Issue #3848).

These tests verify that:
1. Todo.__init__ validates text is not empty (consistent with rename and add)
2. Todo.__init__ validates text is not whitespace-only
3. Error message matches the existing 'Todo text cannot be empty' format
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_empty_text() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="")

    assert "cannot be empty" in str(exc_info.value)


def test_todo_init_rejects_whitespace_only_text() -> None:
    """Todo(id=1, text='   ') should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text="   ")

    assert "cannot be empty" in str(exc_info.value)


def test_todo_init_accepts_valid_text() -> None:
    """Todo(id=1, text='valid') should work normally."""
    todo = Todo(id=1, text="valid")

    assert todo.id == 1
    assert todo.text == "valid"
    assert todo.done is False


def test_todo_init_strips_whitespace_and_accepts() -> None:
    """Todo.__init__ should strip whitespace and accept if not empty."""
    todo = Todo(id=1, text="  valid  ")

    # text should be stripped
    assert todo.text == "valid"


def test_todo_init_error_message_matches_rename() -> None:
    """Error message should be consistent with rename() method."""
    # Get the error from Todo.rename for comparison
    todo = Todo(id=1, text="original")
    with pytest.raises(ValueError) as rename_exc:
        todo.rename("")

    # Now test that __init__ raises the same error
    with pytest.raises(ValueError) as init_exc:
        Todo(id=1, text="")

    # Error messages should match
    assert str(init_exc.value) == str(rename_exc.value)
