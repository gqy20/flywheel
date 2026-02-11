"""Tests for JSON top-level validation (Issue #2882).

These tests verify that TodoStorage.load() properly validates that the JSON
file contains a list at the top level, and rejects other types (dict, string,
number, boolean, null) with clear error messages.

This prevents silent failures where dict iteration would iterate over keys
instead of values, or other unexpected behaviors.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_top_level_dict(tmp_path) -> None:
    """Loading a JSON file with top-level object (dict) should raise ValueError.

    This prevents iterating over dict keys instead of dict values.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file with top-level object (common mistake)
    db.write_text('{"items": [{"id": 1, "text": "task"}]}', encoding="utf-8")

    # Should raise ValueError, not silently iterate over keys
    with pytest.raises(ValueError, match=r"must be a JSON list|JSON list"):
        storage.load()


def test_load_rejects_top_level_string(tmp_path) -> None:
    """Loading a JSON file with top-level string should raise ValueError."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('"not a list"', encoding="utf-8")

    with pytest.raises(ValueError, match=r"must be a JSON list|JSON list"):
        storage.load()


def test_load_rejects_top_level_number(tmp_path) -> None:
    """Loading a JSON file with top-level number should raise ValueError."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text("42", encoding="utf-8")

    with pytest.raises(ValueError, match=r"must be a JSON list|JSON list"):
        storage.load()


def test_load_rejects_top_level_boolean(tmp_path) -> None:
    """Loading a JSON file with top-level boolean should raise ValueError."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text("true", encoding="utf-8")

    with pytest.raises(ValueError, match=r"must be a JSON list|JSON list"):
        storage.load()


def test_load_rejects_top_level_null(tmp_path) -> None:
    """Loading a JSON file with top-level null should raise ValueError."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text("null", encoding="utf-8")

    with pytest.raises(ValueError, match=r"must be a JSON list|JSON list"):
        storage.load()


def test_load_accepts_valid_list(tmp_path) -> None:
    """Loading a JSON file with top-level list should work correctly.

    This is the positive test case ensuring valid JSON lists still work.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Valid JSON list format
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].text == "task2"


def test_load_accepts_empty_list(tmp_path) -> None:
    """Loading an empty JSON list should return empty todo list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text("[]", encoding="utf-8")

    todos = storage.load()
    assert todos == []


def test_error_message_is_clear(tmp_path) -> None:
    """The error message should clearly indicate the problem."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    db.write_text('{"items": []}', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    # Error message should be user-friendly and mention JSON list requirement
    error_msg = str(exc_info.value).lower()
    assert "json list" in error_msg or "must be" in error_msg
