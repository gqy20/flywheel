"""Tests for list item type validation in TodoStorage.load() (Issue #5281).

These tests verify that:
1. When JSON list contains non-dict items (string, int, list), load() raises ValueError
2. The error message is clear and mentions 'JSON objects' or 'dict'
3. Valid JSON list with dict items loads successfully
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_string_list_items(tmp_path) -> None:
    """JSON list with string items should raise clear ValueError, not TypeError."""
    db = tmp_path / "strings.json"
    storage = TodoStorage(str(db))

    # JSON file contains a list of strings, not objects
    db.write_text('["string1", "string2"]', encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"JSON objects|dict"):
        storage.load()


def test_storage_load_rejects_int_list_items(tmp_path) -> None:
    """JSON list with integer items should raise clear ValueError, not TypeError."""
    db = tmp_path / "ints.json"
    storage = TodoStorage(str(db))

    # JSON file contains a list of integers, not objects
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"JSON objects|dict"):
        storage.load()


def test_storage_load_rejects_nested_list_items(tmp_path) -> None:
    """JSON list with nested list items should raise clear ValueError."""
    db = tmp_path / "nested.json"
    storage = TodoStorage(str(db))

    # JSON file contains a list of lists, not objects
    db.write_text('[["a", "b"], ["c"]]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"JSON objects|dict"):
        storage.load()


def test_storage_load_rejects_mixed_invalid_items(tmp_path) -> None:
    """JSON list with mixed valid and invalid items should raise ValueError."""
    db = tmp_path / "mixed.json"
    storage = TodoStorage(str(db))

    # JSON file contains one valid dict and one invalid int
    db.write_text('[{"id": 1, "text": "valid"}, 123]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"JSON objects|dict"):
        storage.load()


def test_storage_load_accepts_valid_dict_items(tmp_path) -> None:
    """JSON list with valid dict items should load successfully."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Valid JSON with dict items
    db.write_text('[{"id": 1, "text": "task1"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].id == 1
    assert todos[0].text == "task1"
