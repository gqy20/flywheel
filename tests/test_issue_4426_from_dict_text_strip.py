"""Tests for from_dict() text stripping behavior (Issue #4426).

These tests verify that:
1. Todo.from_dict strips whitespace from text, consistent with CLI.add() and rename()
2. Roundtrip save/load preserves stripped text
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_from_dict_strips_leading_trailing_whitespace() -> None:
    """Todo.from_dict should strip leading/trailing whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  hello  "})
    assert todo.text == "hello"


def test_from_dict_strips_leading_whitespace() -> None:
    """Todo.from_dict should strip leading whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "   task with spaces"})
    assert todo.text == "task with spaces"


def test_from_dict_strips_trailing_whitespace() -> None:
    """Todo.from_dict should strip trailing whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "task with trailing   "})
    assert todo.text == "task with trailing"


def test_from_dict_strips_newlines() -> None:
    """Todo.from_dict should strip newlines from text."""
    todo = Todo.from_dict({"id": 1, "text": "\n\ntask\n\n"})
    assert todo.text == "task"


def test_from_dict_strips_tabs() -> None:
    """Todo.from_dict should strip tabs from text."""
    todo = Todo.from_dict({"id": 1, "text": "\t\ttask\t\t"})
    assert todo.text == "task"


def test_roundtrip_save_load_preserves_stripped_text(tmp_path) -> None:
    """Save then load should preserve stripped text."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create a todo with whitespace
    todo = Todo.from_dict({"id": 1, "text": "  original text  "})

    # Save and reload
    storage.save([todo])
    loaded_todos = storage.load()

    assert len(loaded_todos) == 1
    assert loaded_todos[0].text == "original text"


def test_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should raise ValueError for whitespace-only text."""
    import pytest

    with pytest.raises(ValueError, match=r"empty"):
        Todo.from_dict({"id": 1, "text": "   "})
