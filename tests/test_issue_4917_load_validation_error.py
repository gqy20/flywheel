"""Tests for load() validation error handling (Issue #4917).

These tests verify that:
1. load() fails-fast with clear error message including item index
2. load() provides all-or-nothing semantics (no partial loads)
3. Error message shows which item and which field failed
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_includes_item_index_in_missing_id_error(tmp_path) -> None:
    """load() should include item index when 'id' field is missing."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # 3 items, where item[1] is missing 'id' field
    db.write_text(
        '''[
        {"id": 1, "text": "first task"},
        {"text": "missing id - should fail"},
        {"id": 3, "text": "third task"}
    ]''',
        encoding="utf-8",
    )

    # Should raise ValueError with item index and field name
    with pytest.raises(ValueError, match=r"item.*1|index.*1|position.*1"):
        storage.load()


def test_load_includes_item_index_in_missing_text_error(tmp_path) -> None:
    """load() should include item index when 'text' field is missing."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # 3 items, where item[2] is missing 'text' field
    db.write_text(
        '''[
        {"id": 1, "text": "first task"},
        {"id": 2, "text": "second task"},
        {"id": 3}
    ]''',
        encoding="utf-8",
    )

    # Should raise ValueError with item index
    with pytest.raises(ValueError, match=r"item.*2|index.*2|position.*2"):
        storage.load()


def test_load_includes_item_index_in_invalid_id_type_error(tmp_path) -> None:
    """load() should include item index when 'id' has wrong type."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # 3 items, where item[0] has invalid id type
    db.write_text(
        '''[
        {"id": "not-an-int", "text": "first task"},
        {"id": 2, "text": "second task"},
        {"id": 3, "text": "third task"}
    ]''',
        encoding="utf-8",
    )

    # Should raise ValueError with item index
    with pytest.raises(ValueError, match=r"item.*0|index.*0|position.*0"):
        storage.load()


def test_load_all_or_nothing_semantics(tmp_path) -> None:
    """load() should not return partial data when an item fails validation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # 3 items, where item[1] is invalid
    db.write_text(
        '''[
        {"id": 1, "text": "first task"},
        {"id": 2},
        {"id": 3, "text": "third task"}
    ]''',
        encoding="utf-8",
    )

    # Should raise error, not return partial list
    with pytest.raises(ValueError):
        storage.load()


def test_load_error_message_includes_specific_field(tmp_path) -> None:
    """load() error message should mention the specific validation failure."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Item missing 'text' field
    db.write_text('[{"id": 1}]', encoding="utf-8")

    # Should mention 'text' field in error
    with pytest.raises(ValueError, match=r"'text'"):
        storage.load()
