"""Tests for text length validation in Todo.from_dict (Issue #6745).

These tests verify that:
1. Todo.from_dict accepts text up to MAX_TEXT_LENGTH characters
2. Todo.from_dict raises ValueError for text exceeding MAX_TEXT_LENGTH
3. Storage roundtrip still works for max-length text
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import MAX_TEXT_LENGTH, Todo


def test_todo_from_dict_accepts_text_at_max_length() -> None:
    """Todo.from_dict should accept text with exactly MAX_TEXT_LENGTH characters."""
    text_at_limit = "x" * MAX_TEXT_LENGTH
    todo = Todo.from_dict({"id": 1, "text": text_at_limit})
    assert todo.text == text_at_limit
    assert len(todo.text) == MAX_TEXT_LENGTH


def test_todo_from_dict_rejects_text_exceeding_max_length() -> None:
    """Todo.from_dict should reject text with more than MAX_TEXT_LENGTH characters."""
    text_over_limit = "x" * (MAX_TEXT_LENGTH + 1)
    with pytest.raises(ValueError, match=r"exceeds maximum length"):
        Todo.from_dict({"id": 1, "text": text_over_limit})


def test_todo_from_dict_rejects_extremely_long_text() -> None:
    """Todo.from_dict should reject extremely long text values (e.g., 1M chars)."""
    extremely_long_text = "x" * 1_000_000
    with pytest.raises(ValueError, match=r"exceeds maximum length"):
        Todo.from_dict({"id": 1, "text": extremely_long_text})


def test_storage_roundtrip_with_max_length_text(tmp_path) -> None:
    """Storage should save and load todos with max-length text correctly."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    text_at_limit = "x" * MAX_TEXT_LENGTH
    todo = Todo(id=1, text=text_at_limit, done=False)

    storage.save([todo])
    loaded = storage.load()

    assert len(loaded) == 1
    assert loaded[0].text == text_at_limit


def test_normal_text_still_works() -> None:
    """Todo.from_dict should still work normally with typical text lengths."""
    normal_texts = [
        "Buy groceries",
        "Complete the project report by Friday",
        "Call mom about birthday plans",
        "Review pull request #1234",
    ]
    for i, text in enumerate(normal_texts):
        todo = Todo.from_dict({"id": i, "text": text})
        assert todo.text == text
