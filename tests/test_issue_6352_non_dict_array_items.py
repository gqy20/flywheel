"""Tests for validating JSON array items are dicts (Issue #6352).

These tests verify that:
1. JSON arrays with non-dict items produce clear ValueError (not TypeError)
2. Error message clearly indicates which item is invalid
3. Common non-dict values (integers, null, strings) are properly rejected
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_json_array_with_integers(tmp_path) -> None:
    """JSON array with integer items should raise ValueError with clear message."""
    db = tmp_path / "invalid_ints.json"
    storage = TodoStorage(str(db))

    # Create JSON with integers instead of dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"item.*0|invalid.*item|must be.*dict|non-dict"):
        storage.load()


def test_load_rejects_json_array_with_null(tmp_path) -> None:
    """JSON array with null items should raise ValueError with clear message."""
    db = tmp_path / "invalid_null.json"
    storage = TodoStorage(str(db))

    # Create JSON with null instead of dict
    db.write_text("[null]", encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"item.*0|invalid.*item|must be.*dict|non-dict"):
        storage.load()


def test_load_rejects_json_array_with_strings(tmp_path) -> None:
    """JSON array with string items should raise ValueError with clear message."""
    db = tmp_path / "invalid_strings.json"
    storage = TodoStorage(str(db))

    # Create JSON with strings instead of dicts
    db.write_text('["not a dict", "also not a dict"]', encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"item.*0|invalid.*item|must be.*dict|non-dict"):
        storage.load()


def test_load_rejects_json_array_with_mixed_invalid_types(tmp_path) -> None:
    """JSON array with mixed invalid types should raise ValueError for first invalid item."""
    db = tmp_path / "invalid_mixed.json"
    storage = TodoStorage(str(db))

    # Create JSON with valid dict followed by invalid integer
    db.write_text('[{"id": 1, "text": "valid"}, 42]', encoding="utf-8")

    # Should raise ValueError indicating item index 1 is invalid
    with pytest.raises(ValueError, match=r"item.*1|index.*1|must be.*dict|non-dict"):
        storage.load()


def test_load_accepts_valid_dict_items(tmp_path) -> None:
    """JSON array with valid dict items should load successfully."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create valid JSON with dict items
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].text == "task2"
