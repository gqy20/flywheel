"""Tests for JSON schema validation in storage (Issue #1923).

These tests verify that:
1. Each item in the JSON list is validated to be a dict before Todo.from_dict() is called
2. Non-dict items produce clear, actionable error messages
3. Error messages include the index of the invalid item for easy debugging

This prevents confusing TypeErrors and ensures early validation with helpful messages.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_handles_non_dict_items_string(tmp_path) -> None:
    """List containing strings should produce clear error message with item index."""
    db = tmp_path / "string_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with a string item instead of dict
    db.write_text('["not a dict", {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message about item type
    with pytest.raises(ValueError, match=r"item.*0.*dict|dict.*item|index.*0"):
        storage.load()


def test_storage_load_handles_non_dict_items_int(tmp_path) -> None:
    """List containing integers should produce clear error message with item index."""
    db = tmp_path / "int_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with an int item instead of dict
    db.write_text('[42, {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message about item type
    with pytest.raises(ValueError, match=r"item.*0.*dict|dict.*item|index.*0"):
        storage.load()


def test_storage_load_handles_non_dict_items_list(tmp_path) -> None:
    """List containing nested lists should produce clear error message."""
    db = tmp_path / "nested_list.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with nested list item
    db.write_text('[["nested", "list"], {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message about item type
    with pytest.raises(ValueError, match=r"item.*0.*dict|dict.*item|index.*0"):
        storage.load()


def test_storage_load_handles_non_dict_items_null(tmp_path) -> None:
    """List containing null values should produce clear error message."""
    db = tmp_path / "null_item.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with null item
    db.write_text('[null, {"id": 1, "text": "valid"}]', encoding="utf-8")

    # Should raise ValueError with clear message about item type
    with pytest.raises(ValueError, match=r"item.*0.*dict|dict.*item|index.*0"):
        storage.load()


def test_storage_load_handles_invalid_item_at_end(tmp_path) -> None:
    """Invalid item at the end of list should include correct index."""
    db = tmp_path / "invalid_at_end.json"
    storage = TodoStorage(str(db))

    # Valid items followed by invalid one
    db.write_text('[{"id": 1, "text": "first"}, {"id": 2, "text": "second"}, "bad"]', encoding="utf-8")

    # Should raise ValueError with index 2 (third item)
    with pytest.raises(ValueError, match=r"item.*2.*dict|dict.*item|index.*2"):
        storage.load()


def test_storage_load_validates_item_type_before_from_dict(tmp_path) -> None:
    """Verify dict type check happens early, preventing confusing TypeErrors."""
    db = tmp_path / "type_check_first.json"
    storage = TodoStorage(str(db))

    # Use an int which would cause 'TypeError: argument of type 'int' is not iterable'
    # if we don't validate item type first
    db.write_text('[123]', encoding="utf-8")

    # Should raise ValueError (schema validation), not TypeError (Python error)
    with pytest.raises(ValueError, match=r"item.*0.*dict|dict.*item|index.*0"):
        storage.load()


def test_storage_load_accepts_all_valid_dict_items(tmp_path) -> None:
    """Valid dict items should still load successfully (regression test)."""
    db = tmp_path / "all_valid.json"
    storage = TodoStorage(str(db))

    # All valid dict items
    db.write_text(
        '[{"id": 1, "text": "first"}, {"id": 2, "text": "second", "done": true}]',
        encoding="utf-8",
    )

    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "first"
    assert todos[1].id == 2
    assert todos[1].done is True
