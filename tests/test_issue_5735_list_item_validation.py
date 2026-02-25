"""Tests for list item validation in load() (Issue #5735).

These tests verify that:
1. Non-dict list items (integers, strings, null) produce clear ValueError
2. Mixed valid/invalid items produce clear ValueError
3. Valid JSON with dict items still works correctly
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_integer_list_items(tmp_path) -> None:
    """JSON file with integer list items should raise clear ValueError."""
    db = tmp_path / "integers.json"
    storage = TodoStorage(str(db))

    # Valid JSON but items are integers, not dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with clear message about JSON objects
    with pytest.raises(ValueError, match=r"items.*must be.*JSON objects|all items.*dict"):
        storage.load()


def test_storage_load_rejects_string_list_items(tmp_path) -> None:
    """JSON file with string list items should raise clear ValueError."""
    db = tmp_path / "strings.json"
    storage = TodoStorage(str(db))

    # Valid JSON but items are strings, not dicts
    db.write_text('["task1", "task2"]', encoding="utf-8")

    # Should raise ValueError with clear message about JSON objects
    with pytest.raises(ValueError, match=r"items.*must be.*JSON objects|all items.*dict"):
        storage.load()


def test_storage_load_rejects_null_list_items(tmp_path) -> None:
    """JSON file with null list items should raise clear ValueError."""
    db = tmp_path / "nulls.json"
    storage = TodoStorage(str(db))

    # Valid JSON but items are null, not dicts
    db.write_text("[null]", encoding="utf-8")

    # Should raise ValueError with clear message about JSON objects
    with pytest.raises(ValueError, match=r"items.*must be.*JSON objects|all items.*dict"):
        storage.load()


def test_storage_load_rejects_mixed_valid_invalid_items(tmp_path) -> None:
    """JSON file with mixed valid dict and invalid items should raise clear ValueError."""
    db = tmp_path / "mixed.json"
    storage = TodoStorage(str(db))

    # Valid JSON but has one valid dict and one integer
    db.write_text('[{"id": 1, "text": "valid"}, 123]', encoding="utf-8")

    # Should raise ValueError with clear message about JSON objects
    with pytest.raises(ValueError, match=r"items.*must be.*JSON objects|all items.*dict"):
        storage.load()


def test_storage_load_accepts_valid_dict_items(tmp_path) -> None:
    """JSON file with valid dict items should still work correctly."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Valid JSON with proper dict items
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2", "done": true}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].text == "task2"
    assert todos[1].done is True
