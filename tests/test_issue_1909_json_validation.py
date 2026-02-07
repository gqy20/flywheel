"""Regression tests for issue #1909: JSON deserialization uses json.loads() without validation.

Issue: JSON deserialization in src/flywheel/storage.py:70 uses json.loads() without
schema validation - malformed JSON could cause unexpected behavior or crashes.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_fails_with_non_list_json(tmp_path) -> None:
    """Issue #1909: Malformed JSON (not a list) should raise clear error.

    Before fix: May pass with unexpected behavior or crash later
    After fix: Should raise ValueError with clear message about expected format
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON that is not a list (a dict instead)
    db.write_text('{"id": 1, "text": "not a list"}', encoding="utf-8")

    # Should raise ValueError, not silently accept
    with pytest.raises(ValueError, match=r"must be a JSON list|expected a list"):
        storage.load()


def test_load_fails_with_json_string(tmp_path) -> None:
    """Issue #1909: JSON string instead of list should raise error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write a JSON string instead of list
    db.write_text('"just a string"', encoding="utf-8")

    with pytest.raises(ValueError, match=r"must be a JSON list|expected a list"):
        storage.load()


def test_load_fails_with_json_number(tmp_path) -> None:
    """Issue #1909: JSON number instead of list should raise error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write a JSON number instead of list
    db.write_text('42', encoding="utf-8")

    with pytest.raises(ValueError, match=r"must be a JSON list|expected a list"):
        storage.load()


def test_load_fails_with_item_missing_id(tmp_path) -> None:
    """Issue #1909: Item missing 'id' field should be caught with clear error.

    Before fix: Raises KeyError: 'id' from from_dict()
    After fix: Should raise ValueError with clear message about missing required field
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with item missing 'id' field
    db.write_text('[{"text": "no id"}]', encoding="utf-8")

    # Should raise ValueError about missing required field, not KeyError
    with pytest.raises(ValueError, match=r"missing.*field|required.*field|'id'"):
        storage.load()


def test_load_fails_with_item_missing_text(tmp_path) -> None:
    """Issue #1909: Item missing 'text' field should be caught with clear error.

    Before fix: Raises KeyError: 'text' from from_dict()
    After fix: Should raise ValueError with clear message about missing required field
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with item missing 'text' field
    db.write_text('[{"id": 1}]', encoding="utf-8")

    # Should raise ValueError about missing required field, not KeyError
    with pytest.raises(ValueError, match=r"missing.*field|required.*field|'text'"):
        storage.load()


def test_load_fails_with_item_empty_dict(tmp_path) -> None:
    """Issue #1909: Empty dict item should be caught with clear error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with empty dict item
    db.write_text('[{}]', encoding="utf-8")

    # Should raise ValueError about missing required fields
    with pytest.raises(ValueError, match=r"missing|required|field"):
        storage.load()


def test_load_fails_with_non_string_text(tmp_path) -> None:
    """Issue #1909: Non-string 'text' field should be caught.

    Before fix: int()/str() coercion silently converts to string
    After fix: Should raise ValueError about type mismatch
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with text as a number (not string)
    db.write_text('[{"id": 1, "text": 123}]', encoding="utf-8")

    # Should raise ValueError about type mismatch
    with pytest.raises(ValueError, match=r"string|type"):
        storage.load()


def test_load_fails_with_text_as_dict(tmp_path) -> None:
    """Issue #1909: 'text' field as dict/object should be caught."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with text as a dict
    db.write_text('[{"id": 1, "text": {"nested": "value"}}]', encoding="utf-8")

    # Should raise ValueError about type mismatch
    with pytest.raises(ValueError, match=r"string|type"):
        storage.load()


def test_load_fails_with_non_numeric_id(tmp_path) -> None:
    """Issue #1909: Non-numeric 'id' field that can't be coerced should be caught.

    Before fix: int() may raise ValueError or produce unexpected results
    After fix: Should raise ValueError with clear message about id type
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with id as non-numeric string
    db.write_text('[{"id": "not_a_number", "text": "test"}]', encoding="utf-8")

    # Should raise ValueError about id type
    with pytest.raises(ValueError, match=r"id|integer|number"):
        storage.load()


def test_load_fails_with_id_as_float(tmp_path) -> None:
    """Issue #1909: Float 'id' should be rejected (ids should be integers).

    Before fix: int(1.5) would truncate to 1 silently
    After fix: Should raise ValueError about id being non-integer
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with id as float
    db.write_text('[{"id": 1.5, "text": "test"}]', encoding="utf-8")

    # Should raise ValueError about id not being integer
    with pytest.raises(ValueError, match=r"id|integer"):
        storage.load()


def test_load_succeeds_with_valid_todos(tmp_path) -> None:
    """Issue #1909: Valid JSON should still load correctly.

    This ensures our fix doesn't break normal operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write valid JSON
    todos = [
        Todo(id=1, text="first todo").to_dict(),
        Todo(id=2, text="second todo", done=True).to_dict(),
    ]
    db.write_text(json.dumps(todos), encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].id == 1
    assert loaded[0].text == "first todo"
    assert loaded[1].id == 2
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True


def test_load_handles_optional_fields_correctly(tmp_path) -> None:
    """Issue #1909: Optional fields should default correctly when missing."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with only required fields
    db.write_text('[{"id": 1, "text": "minimal todo"}]', encoding="utf-8")

    # Should load with defaults for optional fields
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].id == 1
    assert loaded[0].text == "minimal todo"
    assert loaded[0].done is False  # default
    # created_at and updated_at should be set by __post_init__


def test_load_succeeds_with_empty_list(tmp_path) -> None:
    """Issue #1909: Empty list should be handled correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write empty JSON list
    db.write_text('[]', encoding="utf-8")

    # Should load successfully as empty list
    loaded = storage.load()
    assert loaded == []


def test_load_fails_with_non_bool_done(tmp_path) -> None:
    """Issue #1909: Non-boolean 'done' field should be caught or coerced properly.

    Before fix: bool() coercion may produce unexpected results
    After fix: Should raise ValueError about type mismatch for boolean field
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with done as string instead of boolean
    db.write_text('[{"id": 1, "text": "test", "done": "true"}]', encoding="utf-8")

    # Should raise ValueError about type mismatch for boolean field
    with pytest.raises(ValueError, match=r"bool|boolean|done"):
        storage.load()
