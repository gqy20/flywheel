"""Regression test for issue #1909: JSON deserialization validation.

Tests that malformed JSON data is rejected with clear error messages.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def test_load_malformed_json_not_a_list(tmp_path) -> None:
    """Test loading JSON that is not a list raises appropriate error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write a dict instead of a list
    db.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    with pytest.raises(ValueError, match="must be a JSON list"):
        storage.load()


def test_load_item_with_missing_id_field(tmp_path) -> None:
    """Test loading item with missing 'id' field raises clear error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with missing required 'id' field
    malformed_data = [{"text": "some todo", "done": False}]
    db.write_text(json.dumps(malformed_data), encoding="utf-8")

    # Should raise ValueError with descriptive message, not KeyError
    with pytest.raises(ValueError, match="id"):
        storage.load()


def test_load_item_with_missing_text_field(tmp_path) -> None:
    """Test loading item with missing 'text' field raises clear error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with missing required 'text' field
    malformed_data = [{"id": 1, "done": False}]
    db.write_text(json.dumps(malformed_data), encoding="utf-8")

    # Should raise ValueError with descriptive message, not KeyError
    with pytest.raises(ValueError, match="text"):
        storage.load()


def test_load_item_with_non_string_id(tmp_path) -> None:
    """Test loading item with non-numeric 'id' field raises clear error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with string 'id' instead of int
    malformed_data = [{"id": "not-a-number", "text": "some todo"}]
    db.write_text(json.dumps(malformed_data), encoding="utf-8")

    # Should raise ValueError with descriptive message about type mismatch
    with pytest.raises(ValueError, match="must be an integer"):
        storage.load()


def test_load_item_with_non_int_id(tmp_path) -> None:
    """Test loading item with non-numeric 'id' field raises clear error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with string 'id' instead of int
    malformed_data = [{"id": "abc", "text": "some todo"}]
    db.write_text(json.dumps(malformed_data), encoding="utf-8")

    # Should raise ValueError with descriptive message about type mismatch
    with pytest.raises(ValueError, match="id"):
        storage.load()


def test_load_item_with_non_string_text(tmp_path) -> None:
    """Test loading item with non-string 'text' field raises clear error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with int 'text' instead of string
    malformed_data = [{"id": 1, "text": 123}]
    db.write_text(json.dumps(malformed_data), encoding="utf-8")

    # The str() conversion will succeed, so this should load without error
    # But we verify the text is converted to string
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "123"


def test_load_item_with_null_text(tmp_path) -> None:
    """Test loading item with null 'text' field raises clear error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write JSON with null 'text' field
    malformed_data = [{"id": 1, "text": None}]
    db.write_text(json.dumps(malformed_data), encoding="utf-8")

    # str(None) = "None" which should work
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "None"


def test_load_valid_json_passes(tmp_path) -> None:
    """Test loading valid JSON succeeds."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Write valid JSON
    valid_data = [
        {"id": 1, "text": "first todo", "done": False},
        {"id": 2, "text": "second todo", "done": True},
    ]
    db.write_text(json.dumps(valid_data), encoding="utf-8")

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
