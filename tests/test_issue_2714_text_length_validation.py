"""Tests for Todo text length validation (Issue #2714).

These tests verify that:
1. Todo text length is validated at creation (via TodoApp.add())
2. Todo.rename() validates max text length
3. Todo.from_dict() validates max text length
4. Text at the exact limit (10000 chars) is accepted
5. Text exceeding the limit raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo

# Maximum text length constant (must match the one in todo.py)
MAX_TODO_TEXT_LENGTH = 10000


def test_todo_creation_at_text_length_limit_succeeds(tmp_path) -> None:
    """Creating a Todo with text exactly at the character limit should succeed."""
    storage = TodoStorage(str(tmp_path / "test.json"))
    app = TodoApp(db_path=str(tmp_path / "test.json"))
    app.storage = storage

    # Create text at exactly the limit
    text_at_limit = "x" * MAX_TODO_TEXT_LENGTH
    todo = app.add(text_at_limit)

    assert todo.text == text_at_limit
    assert len(todo.text) == MAX_TODO_TEXT_LENGTH


def test_todo_creation_exceeding_text_length_limit_raises_valueerror(tmp_path) -> None:
    """Creating a Todo with text exceeding the limit should raise ValueError."""
    storage = TodoStorage(str(tmp_path / "test.json"))
    app = TodoApp(db_path=str(tmp_path / "test.json"))
    app.storage = storage

    # Create text exceeding the limit
    text_exceeding = "y" * (MAX_TODO_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*limit|max.*length"):
        app.add(text_exceeding)


def test_todo_from_dict_at_text_length_limit_succeeds() -> None:
    """Todo.from_dict with text at the limit should succeed."""
    text_at_limit = "a" * MAX_TODO_TEXT_LENGTH
    todo = Todo.from_dict({"id": 1, "text": text_at_limit})

    assert todo.text == text_at_limit
    assert len(todo.text) == MAX_TODO_TEXT_LENGTH


def test_todo_from_dict_exceeding_text_length_limit_raises_valueerror() -> None:
    """Todo.from_dict with text exceeding the limit should raise ValueError."""
    text_exceeding = "b" * (MAX_TODO_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*limit|max.*length"):
        Todo.from_dict({"id": 1, "text": text_exceeding})


def test_todo_rename_at_text_length_limit_succeeds() -> None:
    """Todo.rename with text at the limit should succeed."""
    todo = Todo(id=1, text="original")

    text_at_limit = "c" * MAX_TODO_TEXT_LENGTH
    todo.rename(text_at_limit)

    assert todo.text == text_at_limit
    assert len(todo.text) == MAX_TODO_TEXT_LENGTH


def test_todo_rename_exceeding_text_length_limit_raises_valueerror() -> None:
    """Todo.rename with text exceeding the limit should raise ValueError."""
    todo = Todo(id=1, text="original")

    text_exceeding = "d" * (MAX_TODO_TEXT_LENGTH + 1)

    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*limit|max.*length"):
        todo.rename(text_exceeding)


def test_todo_empty_text_still_raises_valueerror() -> None:
    """Empty text should still raise ValueError (existing behavior preserved)."""
    todo = Todo(id=1, text="original")

    with pytest.raises(ValueError, match=r"empty"):
        todo.rename("   ")
