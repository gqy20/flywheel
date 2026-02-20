"""Tests for item index context in load() error messages (Issue #4665).

These tests verify that when a specific item in the JSON array fails validation,
the error message includes the item index for easier debugging.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_includes_item_index_for_missing_id(tmp_path) -> None:
    """When item at specific index has missing 'id', error should include index."""
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Valid items at indices 0 and 1, malformed item (missing id) at index 2
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}, {"text": "no id"}]',
        encoding="utf-8",
    )

    # Error message should mention index 2
    with pytest.raises(ValueError, match=r"index 2|item 2|\[2\]"):
        storage.load()


def test_storage_load_includes_item_index_for_missing_text(tmp_path) -> None:
    """When item at specific index has missing 'text', error should include index."""
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Valid item at index 0, malformed item (missing text) at index 1
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2}]',
        encoding="utf-8",
    )

    # Error message should mention index 1
    with pytest.raises(ValueError, match=r"index 1|item 1|\[1\]"):
        storage.load()


def test_storage_load_includes_item_index_for_invalid_done(tmp_path) -> None:
    """When item at specific index has invalid 'done' value, error should include index."""
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Valid items at indices 0-2, malformed item at index 3
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}, {"id": 3, "text": "task3"}, {"id": 4, "text": "task4", "done": "invalid"}]',
        encoding="utf-8",
    )

    # Error message should mention index 3
    with pytest.raises(ValueError, match=r"index 3|item 3|\[3\]"):
        storage.load()


def test_storage_load_includes_item_index_for_wrong_id_type(tmp_path) -> None:
    """When item at specific index has wrong 'id' type, error should include index."""
    db = tmp_path / "malformed.json"
    storage = TodoStorage(str(db))

    # Valid item at index 0, malformed item at index 1
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": "not-an-int", "text": "task2"}]',
        encoding="utf-8",
    )

    # Error message should mention index 1
    with pytest.raises(ValueError, match=r"index 1|item 1|\[1\]"):
        storage.load()


def test_storage_load_still_works_for_valid_data(tmp_path) -> None:
    """Verify load() still works correctly for valid data after fix."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # All valid items
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2", "done": true}]',
        encoding="utf-8",
    )

    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].done is True
