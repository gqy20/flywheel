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


# Tests for Issue #3993 - validate 'id' is a positive integer
def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 as invalid (ids must be positive)."""
    with pytest.raises(ValueError, match=r"'id'.*positive|positive.*'id'"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"'id'.*positive|positive.*'id'"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    todo_large = Todo.from_dict({"id": 999999, "text": "task"})
    assert todo_large.id == 999999
