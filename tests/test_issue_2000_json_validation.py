"""Tests for JSON deserialization error handling (Issue #2000).

These tests verify that:
1. Malformed JSON produces clear error messages
2. Missing required fields (id, text) produce clear error messages
3. Invalid types for required fields produce clear error messages
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_load_handles_malformed_json(tmp_path) -> None:
    """Malformed JSON should produce clear error message instead of raw traceback."""
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Create a file with invalid JSON syntax (truncated/unmatched brackets)
    db.write_text('[{"id": 1, "text": "task1"}', encoding="utf-8")

    # Should raise ValueError with clear message, not JSONDecodeError
    with pytest.raises(ValueError, match=r"invalid json|malformed|parse error"):
        storage.load()


def test_storage_load_handles_missing_id_field(tmp_path) -> None:
    """Valid JSON but missing 'id' field should produce clear error message."""
    db = tmp_path / "missing_id.json"
    storage = TodoStorage(str(db))

    # Valid JSON but missing required 'id' field
    db.write_text('[{"text": "task without id"}]', encoding="utf-8")

    # Should raise clear error about missing 'id' field
    with pytest.raises(ValueError, match=r"missing.*'id'|required.*'id'"):
        storage.load()


def test_storage_load_handles_missing_text_field(tmp_path) -> None:
    """Valid JSON but missing 'text' field should produce clear error message."""
    db = tmp_path / "missing_text.json"
    storage = TodoStorage(str(db))

    # Valid JSON but missing required 'text' field
    db.write_text('[{"id": 1}]', encoding="utf-8")

    # Should raise clear error about missing 'text' field
    with pytest.raises(ValueError, match=r"missing.*'text'|required.*'text'"):
        storage.load()


def test_storage_load_handles_wrong_id_type(tmp_path) -> None:
    """Valid JSON but 'id' is not an integer should produce clear error message."""
    db = tmp_path / "wrong_id_type.json"
    storage = TodoStorage(str(db))

    # Valid JSON but 'id' is a string instead of integer
    db.write_text('[{"id": "not-an-int", "text": "task"}]', encoding="utf-8")

    # Should raise clear error about wrong type for 'id' field
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*type|'id'.*integer"):
        storage.load()


def test_todo_from_dict_handles_missing_id() -> None:
    """Todo.from_dict should provide clear error when 'id' is missing."""
    with pytest.raises(ValueError, match=r"missing.*'id'|required.*'id'"):
        Todo.from_dict({"text": "task"})


def test_todo_from_dict_handles_missing_text() -> None:
    """Todo.from_dict should provide clear error when 'text' is missing."""
    with pytest.raises(ValueError, match=r"missing.*'text'|required.*'text'"):
        Todo.from_dict({"id": 1})


def test_todo_from_dict_handles_wrong_id_type() -> None:
    """Todo.from_dict should provide clear error when 'id' is not an integer."""
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*integer"):
        Todo.from_dict({"id": "not-an-int", "text": "task"})


# Tests for Issue #2125 - validate 'done' field is properly typed
def test_todo_from_dict_rejects_truthy_int_done() -> None:
    """Todo.from_dict should reject non-boolean integers like 2 for 'done' field."""
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*bool|'done'.*boolean"):
        Todo.from_dict({"id": 1, "text": "task", "done": 2})


def test_todo_from_dict_rejects_negative_int_done() -> None:
    """Todo.from_dict should reject negative integers for 'done' field."""
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*bool|'done'.*boolean"):
        Todo.from_dict({"id": 1, "text": "task", "done": -1})


def test_todo_from_dict_rejects_string_done() -> None:
    """Todo.from_dict should reject strings for 'done' field."""
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*bool|'done'.*boolean"):
        Todo.from_dict({"id": 1, "text": "task", "done": "false"})


def test_todo_from_dict_accepts_boolean_done() -> None:
    """Todo.from_dict should accept JSON boolean true/false for 'done' field."""
    todo_true = Todo.from_dict({"id": 1, "text": "task", "done": True})
    assert todo_true.done is True

    todo_false = Todo.from_dict({"id": 2, "text": "task2", "done": False})
    assert todo_false.done is False


def test_todo_from_dict_accepts_legacy_int_done() -> None:
    """Todo.from_dict should accept legacy int values 0 and 1 for 'done' field."""
    todo_true = Todo.from_dict({"id": 1, "text": "task", "done": 1})
    assert todo_true.done is True

    todo_false = Todo.from_dict({"id": 2, "text": "task2", "done": 0})
    assert todo_false.done is False


# Tests for Issue #2829 - validate 'created_at'/'updated_at' field types
def test_todo_from_dict_rejects_dict_created_at() -> None:
    """Todo.from_dict should reject dict type for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*type|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": {"key": "value"}})


def test_todo_from_dict_rejects_list_created_at() -> None:
    """Todo.from_dict should reject list type for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*type|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": ["2024-01-01"]})


def test_todo_from_dict_rejects_int_created_at() -> None:
    """Todo.from_dict should reject int type for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*type|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 1234567890})


def test_todo_from_dict_accepts_none_created_at() -> None:
    """Todo.from_dict should accept None for 'created_at' field (auto-fills via __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})
    # None is converted to empty string, then __post_init__ auto-fills with current time
    assert todo.created_at != ""  # Should be auto-filled with ISO timestamp


def test_todo_from_dict_accepts_empty_string_created_at() -> None:
    """Todo.from_dict should accept empty string for 'created_at' field (auto-fills via __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})
    # Empty string is auto-filled with current time by __post_init__
    assert todo.created_at != ""  # Should be auto-filled with ISO timestamp


def test_todo_from_dict_accepts_valid_string_created_at() -> None:
    """Todo.from_dict should accept valid ISO string for 'created_at' field."""
    iso_time = "2024-01-15T10:30:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": iso_time})
    assert todo.created_at == iso_time


def test_todo_from_dict_rejects_dict_updated_at() -> None:
    """Todo.from_dict should reject dict type for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*type|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": {"key": "value"}})


def test_todo_from_dict_rejects_list_updated_at() -> None:
    """Todo.from_dict should reject list type for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*type|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": ["2024-01-01"]})


def test_todo_from_dict_accepts_none_updated_at() -> None:
    """Todo.from_dict should accept None for 'updated_at' field (defaults to created_at)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": None})
    # None is converted to empty string, then __post_init__ defaults to created_at value
    assert todo.updated_at == todo.created_at  # Should equal created_at


def test_todo_from_dict_accepts_valid_string_updated_at() -> None:
    """Todo.from_dict should accept valid ISO string for 'updated_at' field."""
    iso_time = "2024-01-15T10:30:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": iso_time})
    assert todo.updated_at == iso_time
