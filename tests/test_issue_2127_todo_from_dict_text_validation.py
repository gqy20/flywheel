"""Tests for Todo.from_dict() text validation (Issue #2127).

These tests verify that Todo.from_dict() validates and strips text
the same way Todo.rename() does, rejecting empty and whitespace-only strings.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_string() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_rejects_tabs_only() -> None:
    """Todo.from_dict should reject tab-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": "\t\t"})


def test_todo_from_dict_rejects_newlines_only() -> None:
    """Todo.from_dict should reject newline-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text"):
        Todo.from_dict({"id": 1, "text": "\n\n"})


def test_todo_from_dict_strips_padded_whitespace() -> None:
    """Todo.from_dict should strip leading/trailing whitespace from text."""
    todo = Todo.from_dict({"id": 1, "text": "  valid todo  "})
    assert todo.text == "valid todo"


def test_todo_from_dict_strips_mixed_whitespace() -> None:
    """Todo.from_dict should strip all types of whitespace."""
    todo = Todo.from_dict({"id": 1, "text": "\t\n  valid  \n\t"})
    assert todo.text == "valid"


def test_storage_load_rejects_empty_text_in_json(tmp_path) -> None:
    """TodoStorage.load() should reject JSON entries with empty text."""
    db = tmp_path / "empty_text.json"
    storage = TodoStorage(str(db))

    # Valid JSON but with empty string for 'text'
    db.write_text('[{"id": 1, "text": ""}]', encoding="utf-8")

    # Should raise ValueError about empty text
    with pytest.raises(ValueError, match=r"empty|text"):
        storage.load()


def test_storage_load_rejects_whitespace_only_text_in_json(tmp_path) -> None:
    """TodoStorage.load() should reject JSON entries with whitespace-only text."""
    db = tmp_path / "whitespace_text.json"
    storage = TodoStorage(str(db))

    # Valid JSON but with whitespace for 'text'
    db.write_text('[{"id": 1, "text": "   "}]', encoding="utf-8")

    # Should raise ValueError about empty text
    with pytest.raises(ValueError, match=r"empty|text"):
        storage.load()


def test_storage_load_strips_padded_text_in_json(tmp_path) -> None:
    """TodoStorage.load() should strip whitespace from text in JSON."""
    db = tmp_path / "padded_text.json"
    storage = TodoStorage(str(db))

    # Valid JSON with padded text
    db.write_text('[{"id": 1, "text": "  buy milk  "}]', encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "buy milk"
