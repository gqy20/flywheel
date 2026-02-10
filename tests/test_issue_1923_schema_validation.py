"""Tests for JSON schema validation at storage level (Issue #1923).

These tests verify that TodoStorage.load() validates the structure of JSON data
BEFORE passing it to Todo.from_dict(). This is a security hardening measure to
ensure clear error messages and prevent unhandled exceptions from malformed data.

The vulnerability: storage.py only checks root is a list, not that list items
are dictionaries. Non-dict items (strings, ints, null, nested lists) could cause
unclear KeyErrors or TypeErrors instead of proper validation errors.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_handles_non_dict_item_string(tmp_path) -> None:
    """List containing a string instead of object should produce clear error message."""
    db = tmp_path / "string_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains a string instead of object
    db.write_text('["not a dict", {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message, not KeyError or JSONDecodeError
    with pytest.raises(ValueError, match=r"item at index 0|must be a.*object|must be a.*dict"):
        storage.load()


def test_storage_load_handles_non_dict_item_integer(tmp_path) -> None:
    """List containing an integer instead of object should produce clear error message."""
    db = tmp_path / "int_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains an integer instead of object
    db.write_text('[123, {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"item at index 0|must be a.*object|must be a.*dict"):
        storage.load()


def test_storage_load_handles_nested_list_in_list(tmp_path) -> None:
    """List containing a nested list should produce clear error message."""
    db = tmp_path / "nested_list.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains a nested list instead of object
    db.write_text('[[1, 2, 3], {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"item at index 0|must be a.*object|must be a.*dict"):
        storage.load()


def test_storage_load_handles_null_in_list(tmp_path) -> None:
    """List containing null should produce clear error message."""
    db = tmp_path / "null_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains null instead of object
    db.write_text('[null, {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"item at index 0|must be a.*object|must be a.*dict"):
        storage.load()


def test_storage_load_handles_mixed_invalid_types(tmp_path) -> None:
    """List with multiple types of invalid items should report first error."""
    db = tmp_path / "mixed_types.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with multiple invalid types
    db.write_text('[42, "string", null, [1, 2], {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError about the first invalid item (index 0)
    with pytest.raises(ValueError, match=r"item at index 0|must be a.*object|must be a.*dict"):
        storage.load()


def test_storage_load_handles_all_invalid_items(tmp_path) -> None:
    """List containing only non-dict items should produce clear error message."""
    db = tmp_path / "all_invalid.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but all items are non-dict
    db.write_text('[1, 2, 3, "string"]', encoding="utf-8")

    # Should raise ValueError with clear message about first item
    with pytest.raises(ValueError, match=r"item at index 0|must be a.*object|must be a.*dict"):
        storage.load()


def test_storage_load_handles_boolean_instead_of_object(tmp_path) -> None:
    """List containing boolean instead of object should produce clear error message."""
    db = tmp_path / "bool_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains boolean instead of object
    db.write_text('[true, false, {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"item at index 0|must be a.*object|must be a.*dict"):
        storage.load()


def test_storage_load_handles_empty_list(tmp_path) -> None:
    """Empty list should be accepted (valid edge case)."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    db.write_text('[]', encoding="utf-8")

    # Should load successfully with empty list
    todos = storage.load()
    assert todos == []


def test_storage_load_handles_valid_objects(tmp_path) -> None:
    """List of valid dict objects should load successfully."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].text == "task2"
