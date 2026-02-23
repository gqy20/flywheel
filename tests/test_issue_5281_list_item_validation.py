"""Tests for JSON list item type validation (Issue #5281).

These tests verify that:
1. load() validates that each list item is a dict
2. Primitives (string, int, list) in the JSON array produce clear ValueError
3. Valid todo objects still load correctly
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_list_of_strings(tmp_path) -> None:
    """JSON array with string elements should raise clear ValueError."""
    db = tmp_path / "strings.json"
    storage = TodoStorage(str(db))

    db.write_text('["string1", "string2"]', encoding="utf-8")

    with pytest.raises(ValueError, match=r"dict|JSON object|not primitives"):
        storage.load()


def test_load_rejects_list_of_ints(tmp_path) -> None:
    """JSON array with int elements should raise clear ValueError."""
    db = tmp_path / "ints.json"
    storage = TodoStorage(str(db))

    db.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ValueError, match=r"dict|JSON object|not primitives"):
        storage.load()


def test_load_rejects_list_of_lists(tmp_path) -> None:
    """JSON array with nested list elements should raise clear ValueError."""
    db = tmp_path / "nested.json"
    storage = TodoStorage(str(db))

    db.write_text("[[]]", encoding="utf-8")

    with pytest.raises(ValueError, match=r"dict|JSON object|not primitives"):
        storage.load()


def test_load_rejects_mixed_list_with_primitives(tmp_path) -> None:
    """JSON array with mixed valid/invalid elements should raise clear ValueError."""
    db = tmp_path / "mixed.json"
    storage = TodoStorage(str(db))

    # First item is valid dict, second is string - should fail
    db.write_text('[{"id": 1, "text": "valid"}, "invalid"]', encoding="utf-8")

    with pytest.raises(ValueError, match=r"dict|JSON object|not primitives"):
        storage.load()


def test_load_accepts_valid_todo_objects(tmp_path) -> None:
    """Valid JSON array of todo objects should load correctly."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].text == "task2"


def test_load_error_message_is_clear(tmp_path) -> None:
    """Error message should clearly indicate the issue with clear guidance."""
    db = tmp_path / "bad_data.json"
    storage = TodoStorage(str(db))

    db.write_text('["not a todo"]', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    # Error message should mention 'dict' or 'JSON objects' for clarity
    error_msg = str(exc_info.value).lower()
    assert "dict" in error_msg or "json object" in error_msg
