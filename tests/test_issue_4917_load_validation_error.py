"""Tests for load() validation error handling (Issue #4917).

These tests verify that:
1. If any item in JSON array fails validation, entire load fails with clear error
2. Error message includes item index and specific validation failure
3. Partial loads do not occur - all-or-nothing semantics
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_fails_with_item_index_on_missing_id_field(tmp_path) -> None:
    """load() should fail with error showing item index when 'id' field is missing."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with 3 items where item[1] is missing 'id' field
    db.write_text(
        '[{"id": 1, "text": "valid"}, {"text": "missing id"}, {"id": 3, "text": "also valid"}]',
        encoding="utf-8",
    )

    # Should raise ValueError mentioning item index and missing field
    with pytest.raises(ValueError, match=r"item.*1|index.*1|item 1"):
        storage.load()

    # Also verify the error mentions the specific problem
    with pytest.raises(ValueError, match=r"missing.*'id'|required.*'id'"):
        storage.load()


def test_load_fails_with_item_index_on_missing_text_field(tmp_path) -> None:
    """load() should fail with error showing item index when 'text' field is missing."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON where item[2] is missing 'text' field
    db.write_text(
        '[{"id": 1, "text": "valid"}, {"id": 2, "text": "also valid"}, {"id": 3}]',
        encoding="utf-8",
    )

    # Should raise ValueError mentioning item index 2 and missing 'text'
    with pytest.raises(ValueError, match=r"item.*2|index.*2|item 2"):
        storage.load()

    with pytest.raises(ValueError, match=r"missing.*'text'|required.*'text'"):
        storage.load()


def test_load_fails_with_item_index_on_invalid_id_type(tmp_path) -> None:
    """load() should fail with error showing item index when 'id' has wrong type."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON where item[0] has invalid id type
    db.write_text(
        '[{"id": "not-an-int", "text": "invalid id"}, {"id": 2, "text": "valid"}]',
        encoding="utf-8",
    )

    # Should raise ValueError mentioning item index 0
    with pytest.raises(ValueError, match=r"item.*0|index.*0|item 0"):
        storage.load()


def test_load_fails_with_item_index_on_invalid_done_type(tmp_path) -> None:
    """load() should fail with error showing item index when 'done' has wrong type."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON where item[1] has invalid done value (string instead of bool)
    db.write_text(
        '[{"id": 1, "text": "valid"}, {"id": 2, "text": "bad done", "done": "yes"}]',
        encoding="utf-8",
    )

    # Should raise ValueError mentioning item index 1
    with pytest.raises(ValueError, match=r"item.*1|index.*1|item 1"):
        storage.load()


def test_load_success_with_all_valid_items(tmp_path) -> None:
    """load() should succeed and return all items when all are valid."""
    db = tmp_path / "test.json"
    storage = TodoStorage(str(db))

    # Create JSON with all valid items
    db.write_text(
        '[{"id": 1, "text": "first"}, {"id": 2, "text": "second", "done": true}]',
        encoding="utf-8",
    )

    todos = storage.load()

    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "first"
    assert todos[0].done is False
    assert todos[1].id == 2
    assert todos[1].text == "second"
    assert todos[1].done is True
