"""Tests for list element validation in load() (Issue #4806).

These tests verify that:
1. load() validates each list element is a dict before calling from_dict
2. Clear error messages are provided when list elements are not dicts
3. Normal JSON lists still work correctly
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_list_with_integer_elements(tmp_path) -> None:
    """load() should reject JSON lists with integer elements and provide clear error."""
    db = tmp_path / "int_elements.json"
    storage = TodoStorage(str(db))

    # JSON list with integer elements instead of dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise clear error about element not being a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary|not a dict|dictionary"):
        storage.load()


def test_storage_load_rejects_list_with_string_elements(tmp_path) -> None:
    """load() should reject JSON lists with string elements and provide clear error."""
    db = tmp_path / "string_elements.json"
    storage = TodoStorage(str(db))

    # JSON list with string elements instead of dicts
    db.write_text('["hello", "world"]', encoding="utf-8")

    # Should raise clear error about element not being a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary|not a dict|dictionary"):
        storage.load()


def test_storage_load_rejects_mixed_valid_and_invalid_elements(tmp_path) -> None:
    """load() should reject JSON lists with mixed valid/invalid elements."""
    db = tmp_path / "mixed_elements.json"
    storage = TodoStorage(str(db))

    # JSON list with a valid dict followed by an invalid string
    db.write_text('[{"id": 1, "text": "x"}, "invalid"]', encoding="utf-8")

    # Should raise clear error about element not being a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary|not a dict|dictionary"):
        storage.load()


def test_storage_load_accepts_valid_dict_elements(tmp_path) -> None:
    """load() should accept JSON lists with valid dict elements."""
    db = tmp_path / "valid_elements.json"
    storage = TodoStorage(str(db))

    # JSON list with valid todo dicts
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].text == "task2"
