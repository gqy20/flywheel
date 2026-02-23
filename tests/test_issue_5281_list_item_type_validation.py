"""Tests for JSON list item type validation (Issue #5281).

These tests verify that load() validates JSON list items are dict objects,
providing clear error messages when the list contains primitive types.

Issue: load() did not validate that JSON list items are dicts, causing
unclear TypeError/KeyError when items were strings, ints, or lists.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_list_with_string_items(tmp_path) -> None:
    """JSON list containing strings should produce clear ValueError."""
    db = tmp_path / "strings.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with string items instead of objects
    db.write_text('["string1", "string2"]', encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"JSON objects|dict|must contain"):
        storage.load()


def test_storage_load_rejects_list_with_int_items(tmp_path) -> None:
    """JSON list containing integers should produce clear ValueError."""
    db = tmp_path / "ints.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with integer items instead of objects
    db.write_text('[1, 2, 3]', encoding="utf-8")

    # Should raise ValueError with clear message about JSON objects
    with pytest.raises(ValueError, match=r"JSON objects|dict|must contain"):
        storage.load()


def test_storage_load_rejects_list_with_nested_list_items(tmp_path) -> None:
    """JSON list containing nested lists should produce clear ValueError."""
    db = tmp_path / "nested.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with nested list items instead of objects
    db.write_text('[[1, 2], [3, 4]]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"JSON objects|dict|must contain"):
        storage.load()


def test_storage_load_rejects_list_with_mixed_invalid_items(tmp_path) -> None:
    """JSON list with mixed invalid types should produce clear ValueError."""
    db = tmp_path / "mixed.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with mixed invalid types
    db.write_text('[1, "string", null, true]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"JSON objects|dict|must contain"):
        storage.load()


def test_storage_load_accepts_valid_list_of_dicts(tmp_path) -> None:
    """Valid JSON list with dict items should load successfully."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file with proper todo objects
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].id == 1
    assert loaded[0].text == "task1"
    assert loaded[1].id == 2
    assert loaded[1].text == "task2"
