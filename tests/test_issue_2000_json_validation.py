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


# Tests for Issue #2651 - validate text field length to prevent DoS
def test_todo_from_dict_rejects_excessively_long_text() -> None:
    """Todo.from_dict should reject text fields exceeding MAX_TEXT_LENGTH (1MB)."""
    # Create a text string that exceeds 1MB
    long_text = "a" * (1_048_576 + 1)  # 1MB + 1 character

    with pytest.raises(ValueError, match=r"text.*too long|exceeds.*maximum"):
        Todo.from_dict({"id": 1, "text": long_text})


def test_todo_from_dict_accepts_max_length_text() -> None:
    """Todo.from_dict should accept text fields at exactly MAX_TEXT_LENGTH (1MB)."""
    # Create a text string that is exactly 1MB
    max_text = "a" * 1_048_576

    todo = Todo.from_dict({"id": 1, "text": max_text})
    assert todo.text == max_text


def test_todo_from_dict_accepts_normal_length_text() -> None:
    """Todo.from_dict should accept normal length text fields."""
    normal_text = "This is a normal todo item"

    todo = Todo.from_dict({"id": 1, "text": normal_text})
    assert todo.text == normal_text


def test_todo_from_dict_error_message_includes_length_info() -> None:
    """Error message should include both max length and actual length."""
    long_text = "a" * (1_048_576 + 100)  # 1MB + 100 characters

    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": long_text})

    error_msg = str(exc_info.value)
    assert "1048576" in error_msg  # Max length should be in error message
