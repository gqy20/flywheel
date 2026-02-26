"""Tests for error context with file path in load() (Issue #5928).

These tests verify that when Todo.from_dict raises a ValueError,
the error message includes the file path context for easier debugging.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_error_includes_file_path_for_missing_id(tmp_path) -> None:
    """When a todo record is missing 'id', the error should include the file path."""
    db = tmp_path / "test_todos.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with multiple records, where one is invalid
    db.write_text(
        '[{"id": 1, "text": "valid task"}, {"text": "missing id"}]',
        encoding="utf-8",
    )

    # The error message should include the file path
    with pytest.raises(ValueError, match=str(db)) as exc_info:
        storage.load()

    # Also verify the original error about missing 'id' is preserved
    assert "id" in str(exc_info.value).lower()


def test_load_error_includes_file_path_for_missing_text(tmp_path) -> None:
    """When a todo record is missing 'text', the error should include the file path."""
    db = tmp_path / "test_todos.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with multiple records, where one is invalid
    db.write_text(
        '[{"id": 1, "text": "valid task"}, {"id": 2}]',
        encoding="utf-8",
    )

    # The error message should include the file path
    with pytest.raises(ValueError, match=str(db)) as exc_info:
        storage.load()

    # Also verify the original error about missing 'text' is preserved
    assert "text" in str(exc_info.value).lower()


def test_load_error_includes_record_index_for_missing_field(tmp_path) -> None:
    """When a todo record is invalid, the error should indicate the record index."""
    db = tmp_path / "test_todos.json"
    storage = TodoStorage(str(db))

    # Create a JSON file where the 2nd record (index 1) is invalid
    db.write_text(
        '[{"id": 1, "text": "valid task"}, {"id": 2}, {"id": 3, "text": "another valid"}]',
        encoding="utf-8",
    )

    # The error message should indicate which record caused the problem
    with pytest.raises(ValueError, match=r"record.*(1|2)") as exc_info:
        storage.load()

    # Also verify the file path is included
    assert str(db) in str(exc_info.value)


def test_load_error_includes_file_path_for_wrong_type(tmp_path) -> None:
    """When a todo record has wrong type, the error should include the file path."""
    db = tmp_path / "test_todos.json"
    storage = TodoStorage(str(db))

    # Create a JSON file where id is not an integer
    db.write_text(
        '[{"id": "not-an-int", "text": "task"}]',
        encoding="utf-8",
    )

    # The error message should include the file path
    with pytest.raises(ValueError, match=str(db)) as exc_info:
        storage.load()

    # Also verify the original error about 'id' type is preserved
    assert "id" in str(exc_info.value).lower()
