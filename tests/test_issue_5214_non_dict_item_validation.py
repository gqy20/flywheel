"""Tests for non-dict item validation in load() (Issue #5214).

These tests verify that:
1. Non-dict items in JSON array produce clear error messages with element index
2. Error messages specify what type was received and what was expected
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_string_item_in_array(tmp_path) -> None:
    """JSON array containing a string should produce clear error with index."""
    db = tmp_path / "invalid_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON array but element is a string, not an object
    db.write_text('["not a dict"]', encoding="utf-8")

    # Should raise clear error mentioning the element index and type
    with pytest.raises(ValueError, match=r"element.*(0|index 0).*object|object.*element"):
        storage.load()


def test_storage_load_rejects_number_item_in_array(tmp_path) -> None:
    """JSON array containing a number should produce clear error with index."""
    db = tmp_path / "invalid_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON array but elements are numbers, not objects
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise clear error mentioning the element index
    with pytest.raises(ValueError, match=r"element.*(0|index 0).*object"):
        storage.load()


def test_storage_load_rejects_null_item_in_array(tmp_path) -> None:
    """JSON array containing null should produce clear error with index."""
    db = tmp_path / "invalid_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON array but element is null
    db.write_text("[null]", encoding="utf-8")

    # Should raise clear error mentioning null is not valid
    with pytest.raises(ValueError, match=r"element.*(0|index 0).*object|null.*not"):
        storage.load()


def test_storage_load_rejects_list_item_in_array(tmp_path) -> None:
    """JSON array containing nested list should produce clear error with index."""
    db = tmp_path / "invalid_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON array but element is nested list
    db.write_text("[[1, 2, 3]]", encoding="utf-8")

    # Should raise clear error mentioning the element is a list, not object
    with pytest.raises(ValueError, match=r"element.*(0|index 0).*object"):
        storage.load()


def test_storage_load_rejects_non_dict_item_with_correct_index(tmp_path) -> None:
    """Error message should indicate the correct index of problematic element."""
    db = tmp_path / "invalid_item.json"
    storage = TodoStorage(str(db))

    # Valid objects followed by invalid string at index 2
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}, "invalid"]',
        encoding="utf-8",
    )

    # Should raise clear error mentioning index 2
    with pytest.raises(ValueError, match=r"index 2|element 2"):
        storage.load()


def test_storage_load_accepts_valid_dict_items(tmp_path) -> None:
    """Valid dict items should load successfully."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Valid JSON array of objects
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2", "done": true}]',
        encoding="utf-8",
    )

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].done is True
