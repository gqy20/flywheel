"""Tests for empty/whitespace text validation in Todo.from_dict() (Issue #2127).

These tests verify that:
1. Todo.from_dict() rejects empty string ('') for text field
2. Todo.from_dict() rejects whitespace-only text ('   ')
3. Todo.from_dict() strips and accepts padded valid text ('  valid  ')
4. Storage.load() properly rejects JSON with empty/whitespace text
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text.*empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only strings for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text.*empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_rejects_tab_only_text() -> None:
    """Todo.from_dict should reject tab-only strings for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|text.*empty|cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\t"})


def test_todo_from_dict_strips_padded_valid_text() -> None:
    """Todo.from_dict should strip leading/trailing whitespace from valid text."""
    todo = Todo.from_dict({"id": 1, "text": "  valid task  "})
    assert todo.text == "valid task"


def test_todo_from_dict_strips_mixed_whitespace() -> None:
    """Todo.from_dict should strip mixed whitespace (spaces, tabs) from valid text."""
    todo = Todo.from_dict({"id": 1, "text": "\t  valid task  \t"})
    assert todo.text == "valid task"


def test_storage_load_rejects_empty_text(tmp_path) -> None:
    """TodoStorage.load() should reject JSON with empty text field."""
    db = tmp_path / "empty_text.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": ""}]', encoding="utf-8")

    with pytest.raises(ValueError, match=r"empty|text.*empty|cannot be empty"):
        storage.load()


def test_storage_load_rejects_whitespace_only_text(tmp_path) -> None:
    """TodoStorage.load() should reject JSON with whitespace-only text field."""
    db = tmp_path / "whitespace_text.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "   "}]', encoding="utf-8")

    with pytest.raises(ValueError, match=r"empty|text.*empty|cannot be empty"):
        storage.load()


def test_storage_load_strips_padded_text(tmp_path) -> None:
    """TodoStorage.load() should strip whitespace from valid text in JSON."""
    db = tmp_path / "padded_text.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "  padded task  "}]', encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "padded task"
