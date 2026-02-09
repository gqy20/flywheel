"""Regression test for Issue #2566 - TypeError when JSON array contains null items."""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_load_handles_null_items_gracefully(tmp_path) -> None:
    """Bug #2566: JSON arrays containing null items should be handled gracefully.

    The fix should either:
    1. Filter out null items with a warning, or
    2. Raise a clear ValueError indicating which item is invalid

    This test verifies the behavior is well-defined and doesn't crash
    with a cryptic TypeError.
    """
    db = tmp_path / "with_nulls.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with null items in the array
    # Pattern: [{"id":1,"text":"valid"}, null, {"id":2,"text":"also_valid"}]
    payload = [
        {"id": 1, "text": "first todo"},
        None,
        {"id": 2, "text": "second todo"},
        None,
        None,
        {"id": 3, "text": "third todo"},
    ]
    db.write_text(json.dumps(payload), encoding="utf-8")

    # Should either:
    # 1. Load only valid items (filtering out nulls), or
    # 2. Raise a clear ValueError
    result = storage.load()

    # If we get here, null items were filtered out
    # Verify we got the valid items
    assert len(result) == 3
    assert result[0].id == 1
    assert result[0].text == "first todo"
    assert result[1].id == 2
    assert result[1].text == "second todo"
    assert result[2].id == 3
    assert result[2].text == "third todo"


def test_storage_load_with_all_null_items(tmp_path) -> None:
    """Bug #2566: Edge case - JSON array with only null items."""
    db = tmp_path / "all_nulls.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with only null items
    payload = [None, None, None]
    db.write_text(json.dumps(payload), encoding="utf-8")

    # Should return empty list (all nulls filtered)
    result = storage.load()
    assert result == []


def test_storage_load_with_null_at_beginning(tmp_path) -> None:
    """Bug #2566: Edge case - null items at the beginning of array."""
    db = tmp_path / "null_first.json"
    storage = TodoStorage(str(db))

    # Null at the beginning
    payload = [None, {"id": 1, "text": "after null"}]
    db.write_text(json.dumps(payload), encoding="utf-8")

    result = storage.load()
    assert len(result) == 1
    assert result[0].id == 1


def test_storage_load_with_null_at_end(tmp_path) -> None:
    """Bug #2566: Edge case - null items at the end of array."""
    db = tmp_path / "null_last.json"
    storage = TodoStorage(str(db))

    # Null at the end
    payload = [{"id": 1, "text": "before null"}, None]
    db.write_text(json.dumps(payload), encoding="utf-8")

    result = storage.load()
    assert len(result) == 1
    assert result[0].id == 1


def test_todo_from_dict_with_none_raises_clear_error() -> None:
    """Bug #2566: Verify Todo.from_dict handles None with a clear error message."""
    # Calling from_dict with None should raise a clear ValueError
    # indicating that None is not a valid todo item
    with pytest.raises(ValueError, match=r"null|None|invalid"):
        Todo.from_dict(None)  # type: ignore
