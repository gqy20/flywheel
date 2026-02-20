"""Tests for Issue #4763: load() error messages include item index.

When load() processes a JSON array and an item fails to parse,
the error message should indicate which item (by index) caused the failure.
This makes debugging data issues much easier.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_error_includes_index_for_missing_id(tmp_path) -> None:
    """When item at index N is missing 'id', error message should include index N."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create JSON with 3 items, where the 3rd (index 2) is missing 'id'
    db.write_text(
        '[{"id": 1, "text": "first"}, {"id": 2, "text": "second"}, {"text": "no id"}]',
        encoding="utf-8",
    )

    # Error should mention index 2
    with pytest.raises(ValueError, match=r"index 2|item 2|record 2|position 2"):
        storage.load()


def test_load_error_includes_index_for_missing_text(tmp_path) -> None:
    """When item at index N is missing 'text', error message should include index N."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create JSON with 3 items, where the 2nd (index 1) is missing 'text'
    db.write_text(
        '[{"id": 1, "text": "first"}, {"id": 2}, {"id": 3, "text": "third"}]',
        encoding="utf-8",
    )

    # Error should mention index 1
    with pytest.raises(ValueError, match=r"index 1|item 1|record 1|position 1"):
        storage.load()


def test_load_error_includes_index_for_invalid_id_type(tmp_path) -> None:
    """When item at index N has invalid 'id' type, error message should include index N."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create JSON with 5 items, where the 5th (index 4) has invalid id
    db.write_text(
        '[{"id": 1, "text": "a"}, {"id": 2, "text": "b"}, {"id": 3, "text": "c"}, '
        '{"id": 4, "text": "d"}, {"id": "invalid", "text": "e"}]',
        encoding="utf-8",
    )

    # Error should mention index 4
    with pytest.raises(ValueError, match=r"index 4|item 4|record 4|position 4"):
        storage.load()


def test_load_error_includes_index_for_invalid_done_type(tmp_path) -> None:
    """When item at index N has invalid 'done' type, error message should include index N."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create JSON with 2 items, where the 1st (index 0) has invalid done value
    db.write_text(
        '[{"id": 1, "text": "first", "done": "yes"}, {"id": 2, "text": "second"}]',
        encoding="utf-8",
    )

    # Error should mention index 0
    with pytest.raises(ValueError, match=r"index 0|item 0|record 0|position 0"):
        storage.load()


def test_load_success_with_valid_data(tmp_path) -> None:
    """Load should succeed and return correct todos when all data is valid."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create valid JSON with multiple items
    db.write_text(
        '[{"id": 1, "text": "first", "done": true}, '
        '{"id": 2, "text": "second", "done": false}, '
        '{"id": 3, "text": "third"}]',
        encoding="utf-8",
    )

    todos = storage.load()

    assert len(todos) == 3
    assert todos[0].id == 1
    assert todos[0].text == "first"
    assert todos[0].done is True
    assert todos[1].id == 2
    assert todos[1].text == "second"
    assert todos[1].done is False
    assert todos[2].id == 3
    assert todos[2].text == "third"
