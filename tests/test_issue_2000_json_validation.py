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


# Tests for Issue #5352 - validate JSON array elements are dicts
def test_storage_load_rejects_int_array_elements(tmp_path) -> None:
    """TodoStorage.load should reject JSON arrays containing non-dict elements like ints.

    Issue #5352: When JSON array contains [1, 2, 3], should raise clear ValueError
    instead of confusing TypeError.
    """
    db = tmp_path / "int_array.json"
    storage = TodoStorage(str(db))

    # JSON array with integer elements instead of dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with clear message about element index and expected type
    with pytest.raises(ValueError, match=r"element.*index|index.*0|expected.*dict|must be a dict"):
        storage.load()


def test_storage_load_rejects_string_array_elements(tmp_path) -> None:
    """TodoStorage.load should reject JSON arrays containing non-dict elements like strings.

    Issue #5352: When JSON array contains ["string"], should raise clear ValueError
    instead of confusing TypeError.
    """
    db = tmp_path / "string_array.json"
    storage = TodoStorage(str(db))

    # JSON array with string elements instead of dicts
    db.write_text('["not a dict", "also not a dict"]', encoding="utf-8")

    # Should raise ValueError with clear message about element index and expected type
    with pytest.raises(ValueError, match=r"element.*index|index.*0|expected.*dict|must be a dict"):
        storage.load()


def test_storage_load_rejects_mixed_array_with_non_dict(tmp_path) -> None:
    """TodoStorage.load should reject JSON arrays where some elements are not dicts.

    Issue #5352: Should report the specific index of the invalid element.
    """
    db = tmp_path / "mixed_array.json"
    storage = TodoStorage(str(db))

    # JSON array with mixed valid/invalid elements
    db.write_text('[{"id": 1, "text": "valid"}, 42]', encoding="utf-8")

    # Should raise ValueError pointing to index 1
    with pytest.raises(ValueError, match=r"index.*1|element.*1"):
        storage.load()
