"""Tests for non-dict array item validation (Issue #6352).

These tests verify that:
1. load() raises ValueError (not TypeError) when JSON array contains non-dict items
2. Error message clearly indicates which item in the array is invalid
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_json_array_with_integers(tmp_path) -> None:
    """load() should raise ValueError with clear message when JSON array contains integers."""
    db = tmp_path / "int_items.json"
    storage = TodoStorage(str(db))

    # JSON array containing integers instead of dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"item.*0|non-dict|invalid.*item"):
        storage.load()


def test_storage_load_rejects_json_array_with_nulls(tmp_path) -> None:
    """load() should raise ValueError with clear message when JSON array contains null."""
    db = tmp_path / "null_items.json"
    storage = TodoStorage(str(db))

    # JSON array containing null
    db.write_text("[null]", encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"item.*0|non-dict|invalid.*item"):
        storage.load()


def test_storage_load_rejects_json_array_with_strings(tmp_path) -> None:
    """load() should raise ValueError with clear message when JSON array contains strings."""
    db = tmp_path / "string_items.json"
    storage = TodoStorage(str(db))

    # JSON array containing strings
    db.write_text('["not a todo"]', encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"item.*0|non-dict|invalid.*item"):
        storage.load()


def test_storage_load_rejects_json_array_with_mixed_invalid_item(tmp_path) -> None:
    """load() should identify the specific index of the invalid item in mixed array."""
    db = tmp_path / "mixed_items.json"
    storage = TodoStorage(str(db))

    # JSON array with valid dict followed by invalid item
    db.write_text('[{"id": 1, "text": "valid"}, 42]', encoding="utf-8")

    # Should raise ValueError and mention index 1
    with pytest.raises(ValueError, match=r"item.*1|index.*1"):
        storage.load()


def test_storage_load_accepts_valid_dict_array(tmp_path) -> None:
    """load() should accept valid JSON array of dict items."""
    db = tmp_path / "valid_items.json"
    storage = TodoStorage(str(db))

    # Valid JSON array of todo dicts
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[1].id == 2
