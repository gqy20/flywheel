"""Regression tests for issue #2000: JSON deserialization error handling.

Tests that malformed JSON and missing required fields are handled gracefully
with clear error messages instead of raw stack traces.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_load_handles_malformed_json_missing_bracket(tmp_path) -> None:
    """Malformed JSON (missing closing bracket) should raise ValueError with clear message."""
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Write malformed JSON (missing closing bracket)
    db.write_text('[{"id": 1, "text": "test"}', encoding="utf-8")

    # Should raise ValueError with clear message, not JSONDecodeError
    with pytest.raises(ValueError, match=r"malformed|invalid|parse"):
        storage.load()


def test_storage_load_handles_malformed_json_truncated(tmp_path) -> None:
    """Truncated JSON file should raise ValueError with clear message."""
    db = tmp_path / "truncated.json"
    storage = TodoStorage(str(db))

    # Write truncated JSON
    db.write_text('{"id": 1, "text": "test"', encoding="utf-8")

    # Should raise ValueError with clear message, not JSONDecodeError
    with pytest.raises(ValueError, match=r"malformed|invalid|parse"):
        storage.load()


def test_storage_load_handles_invalid_json_syntax(tmp_path) -> None:
    """Invalid JSON syntax (e.g., trailing comma) should raise ValueError."""
    db = tmp_path / "invalid_syntax.json"
    storage = TodoStorage(str(db))

    # Write JSON with syntax error (trailing comma)
    db.write_text('[{"id": 1, "text": "test",}]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"malformed|invalid|parse"):
        storage.load()


def test_todo_from_dict_handles_missing_id_field() -> None:
    """Missing 'id' field should raise ValueError with clear message."""
    data = {"text": "test"}

    # Should raise ValueError with clear message about missing field, not KeyError
    with pytest.raises(ValueError, match=r"id|required|missing"):
        Todo.from_dict(data)


def test_todo_from_dict_handles_missing_text_field() -> None:
    """Missing 'text' field should raise ValueError with clear message."""
    data = {"id": 1}

    # Should raise ValueError with clear message about missing field, not KeyError
    with pytest.raises(ValueError, match=r"text|required|missing"):
        Todo.from_dict(data)


def test_todo_from_dict_handles_wrong_type_for_id() -> None:
    """Wrong type for 'id' (non-integer) should raise ValueError."""
    data = {"id": "not-an-int", "text": "test"}

    # Should raise ValueError with clear message about type error
    with pytest.raises(ValueError, match=r"id|integer|type"):
        Todo.from_dict(data)


def test_todo_from_dict_handles_wrong_type_for_text() -> None:
    """Wrong type for 'text' (non-string) should raise ValueError."""
    data = {"id": 1, "text": 123}

    # Should raise ValueError with clear message about type error
    with pytest.raises(ValueError, match=r"text|string|type"):
        Todo.from_dict(data)


def test_storage_load_handles_todos_with_missing_fields(tmp_path) -> None:
    """Storage load should handle todos with missing required fields gracefully."""
    db = tmp_path / "missing_fields.json"
    storage = TodoStorage(str(db))

    # Write JSON with todo missing required field
    db.write_text('[{"id": 1, "text": "valid"}, {"id": 2}]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"text|required|missing"):
        storage.load()
