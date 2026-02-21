"""Tests for issue #4917: load() should report item index on validation failure.

This test suite verifies that when TodoStorage.load() encounters invalid data,
it provides clear error messages including:
1. The index of the failing item in the JSON array
2. The specific validation failure reason

This ensures all-or-nothing semantics with no silent data loss.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_reports_item_index_on_missing_id(tmp_path) -> None:
    """load() should report which item index failed when 'id' is missing."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with 3 items where item[1] is missing 'id' field
    db.write_text(
        '[{"id": 1, "text": "valid"}, {"text": "missing id"}, {"id": 3, "text": "also valid"}]',
        encoding="utf-8",
    )

    # Should raise ValueError mentioning item index 1 and missing 'id'
    with pytest.raises(ValueError, match=r"item.*1|index.*1|position.*1") as exc_info:
        storage.load()

    # Error message should also mention the specific validation failure
    error_msg = str(exc_info.value).lower()
    assert "id" in error_msg, "Error message should mention 'id' field"


def test_load_reports_item_index_on_missing_text(tmp_path) -> None:
    """load() should report which item index failed when 'text' is missing."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with 3 items where item[2] is missing 'text' field
    db.write_text(
        '[{"id": 1, "text": "valid"}, {"id": 2, "text": "also valid"}, {"id": 3}]',
        encoding="utf-8",
    )

    # Should raise ValueError mentioning item index 2 and missing 'text'
    with pytest.raises(ValueError, match=r"item.*2|index.*2|position.*2") as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    assert "text" in error_msg, "Error message should mention 'text' field"


def test_load_reports_item_index_on_invalid_id_type(tmp_path) -> None:
    """load() should report which item index failed when 'id' has wrong type."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with 3 items where item[0] has invalid 'id' type
    db.write_text(
        '[{"id": "not-an-int", "text": "invalid id"}, {"id": 2, "text": "valid"}, {"id": 3, "text": "valid"}]',
        encoding="utf-8",
    )

    # Should raise ValueError mentioning item index 0
    with pytest.raises(ValueError, match=r"item.*0|index.*0|position.*0"):
        storage.load()


def test_load_reports_item_index_on_invalid_done_type(tmp_path) -> None:
    """load() should report which item index failed when 'done' has wrong type."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with 3 items where item[1] has invalid 'done' type
    db.write_text(
        '[{"id": 1, "text": "valid"}, {"id": 2, "text": "invalid done", "done": 2}, {"id": 3, "text": "valid"}]',
        encoding="utf-8",
    )

    # Should raise ValueError mentioning item index 1
    with pytest.raises(ValueError, match=r"item.*1|index.*1|position.*1") as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    assert "done" in error_msg, "Error message should mention 'done' field"


def test_load_all_or_nothing_no_partial_loads(tmp_path) -> None:
    """load() should fail completely, not return partial data when any item is invalid."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with first item valid, second invalid
    db.write_text(
        '[{"id": 1, "text": "valid first"}, {"id": 2}]',  # second missing 'text'
        encoding="utf-8",
    )

    # Should raise exception - no partial result
    with pytest.raises(ValueError):
        storage.load()

    # This test verifies all-or-nothing: if load() had returned partial data
    # before failing, that would be the bug we're fixing


def test_load_valid_data_still_works(tmp_path) -> None:
    """Verify that valid data still loads correctly after the fix."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create valid JSON with multiple items
    db.write_text(
        '[{"id": 1, "text": "first"}, {"id": 2, "text": "second", "done": true}, {"id": 3, "text": "third"}]',
        encoding="utf-8",
    )

    todos = storage.load()
    assert len(todos) == 3
    assert todos[0].text == "first"
    assert todos[1].done is True
    assert todos[2].text == "third"
