"""Regression tests for Issue #2621: Todo constructor lacks validation for empty text.

This test file ensures that Todo() constructor validates text content
when instantiated directly, matching the validation in Todo.rename() and TodoApp.add().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_empty_string() -> None:
    """Bug #2621: Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_todo_constructor_rejects_whitespace_only() -> None:
    """Bug #2621: Todo(id=1, text='   ') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\t")


def test_todo_constructor_rejects_newlines_and_tabs() -> None:
    """Bug #2621: Todo(id=1, text='\\n\\t') should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="\n\t")


def test_todo_constructor_accepts_valid_text() -> None:
    """Bug #2621: Todo(id=1, text='valid text') should succeed."""
    todo = Todo(id=1, text="valid task")
    assert todo.text == "valid task"


def test_todo_constructor_strips_whitespace() -> None:
    """Bug #2621: Whitespace around text should be stripped, matching rename() behavior."""
    todo = Todo(id=1, text="  padded  ")
    assert todo.text == "padded"


def test_todo_from_dict_bypasses_validation() -> None:
    """Bug #2621: from_dict should still work (bypasses validation since data comes from storage)."""
    # from_dict is used when loading from storage, so it should accept
    # data that might have empty text (existing data compatibility)
    todo = Todo.from_dict({"id": 1, "text": "from storage"})
    assert todo.id == 1
    assert todo.text == "from storage"
