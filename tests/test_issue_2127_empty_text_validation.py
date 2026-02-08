"""Tests for empty/whitespace text validation in from_dict() (Issue #2127).

These tests verify that Todo.from_dict() properly validates that:
1. Empty string text is rejected
2. Whitespace-only text is rejected
3. Text with padding is stripped (matching rename() behavior)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"text.*empty|text.*cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"text.*empty|text.*cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_todo_from_dict_rejects_tabs_only_text() -> None:
    """Todo.from_dict should reject tabs-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"text.*empty|text.*cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\t"})


def test_todo_from_dict_strips_padded_text() -> None:
    """Todo.from_dict should strip whitespace from text, matching rename() behavior."""
    todo = Todo.from_dict({"id": 1, "text": "  padded task  "})
    assert todo.text == "padded task"


def test_todo_from_dict_accepts_valid_text() -> None:
    """Todo.from_dict should accept valid non-empty text."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.text == "valid task"


def test_storage_load_rejects_empty_text(tmp_path) -> None:
    """TodoStorage.load should reject todos with empty text in JSON."""
    from flywheel.storage import TodoStorage

    db = tmp_path / "empty_text.json"
    storage = TodoStorage(str(db))
    db.write_text('[{"id": 1, "text": ""}]', encoding="utf-8")

    with pytest.raises(ValueError, match=r"text.*empty|text.*cannot be empty"):
        storage.load()


def test_storage_load_rejects_whitespace_text(tmp_path) -> None:
    """TodoStorage.load should reject todos with whitespace-only text in JSON."""
    from flywheel.storage import TodoStorage

    db = tmp_path / "whitespace_text.json"
    storage = TodoStorage(str(db))
    db.write_text('[{"id": 1, "text": "   "}]', encoding="utf-8")

    with pytest.raises(ValueError, match=r"text.*empty|text.*cannot be empty"):
        storage.load()


def test_storage_load_strips_padded_text(tmp_path) -> None:
    """TodoStorage.load should strip whitespace from text in JSON."""
    from flywheel.storage import TodoStorage

    db = tmp_path / "padded_text.json"
    storage = TodoStorage(str(db))
    db.write_text('[{"id": 1, "text": "  padded  "}]', encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "padded"
