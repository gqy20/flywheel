"""Tests for non-dict item validation in load() (Issue #5214).

These tests verify that:
1. JSON arrays with non-dict elements produce clear error messages
2. Error messages include the index of the problematic element
3. Various non-dict types (string, int, null, array) are all detected
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_string_item_in_list(tmp_path) -> None:
    """JSON list with string element should produce clear error message."""
    db = tmp_path / "invalid_string_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON array but contains a string instead of dict
    db.write_text('["not a dict"]', encoding="utf-8")

    # Should raise clear error about element type, not cryptic KeyError
    with pytest.raises(ValueError, match=r"element.*must be.*object|item.*must be.*dict"):
        storage.load()


def test_storage_load_rejects_int_item_in_list(tmp_path) -> None:
    """JSON list with integer element should produce clear error message."""
    db = tmp_path / "invalid_int_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON array but contains integers instead of dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise clear error about element type
    with pytest.raises(ValueError, match=r"element.*must be.*object|item.*must be.*dict"):
        storage.load()


def test_storage_load_rejects_null_item_in_list(tmp_path) -> None:
    """JSON list with null element should produce clear error message."""
    db = tmp_path / "invalid_null_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON array but contains null instead of dict
    db.write_text("[null]", encoding="utf-8")

    # Should raise clear error about element type
    with pytest.raises(ValueError, match=r"element.*must be.*object|item.*must be.*dict"):
        storage.load()


def test_storage_load_rejects_nested_array_item_in_list(tmp_path) -> None:
    """JSON list with nested array element should produce clear error message."""
    db = tmp_path / "invalid_array_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON array but contains nested array instead of dict
    db.write_text('[[1, 2], [3, 4]]', encoding="utf-8")

    # Should raise clear error about element type
    with pytest.raises(ValueError, match=r"element.*must be.*object|item.*must be.*dict"):
        storage.load()


def test_storage_load_error_includes_element_index(tmp_path) -> None:
    """Error message should include the index of the problematic element."""
    db = tmp_path / "invalid_item_with_index.json"
    storage = TodoStorage(str(db))

    # Valid JSON array where second element is invalid
    db.write_text('[{"id": 1, "text": "valid"}, "invalid"]', encoding="utf-8")

    # Error message should mention index 1 (second element)
    with pytest.raises(ValueError, match=r"index 1|position 1|element 1"):
        storage.load()


def test_storage_load_error_includes_element_index_for_mixed_types(tmp_path) -> None:
    """Error message should correctly identify index in mixed valid/invalid list."""
    db = tmp_path / "mixed_valid_invalid.json"
    storage = TodoStorage(str(db))

    # Valid JSON array where third element is invalid (integer)
    db.write_text(
        '[{"id": 1, "text": "first"}, {"id": 2, "text": "second"}, 42]',
        encoding="utf-8",
    )

    # Error message should mention index 2 (third element)
    with pytest.raises(ValueError, match=r"index 2|position 2|element 2"):
        storage.load()
