"""Tests for load() error context (Issue #5928).

These tests verify that when Todo.from_dict raises ValueError during load(),
the error message includes the file path context for easier debugging.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_includes_file_path_in_missing_id_error(tmp_path) -> None:
    """When a todo record is missing 'id', the error should include the file path."""
    db = tmp_path / "my_todos.json"
    storage = TodoStorage(str(db))

    # Create a file with multiple records, the second one missing 'id'
    db.write_text(
        '[{"id": 1, "text": "valid task"}, {"text": "missing id"}]',
        encoding="utf-8",
    )

    # Should raise ValueError that includes the file path
    with pytest.raises(ValueError, match=r"my_todos\.json") as exc_info:
        storage.load()

    # Also verify it still mentions the actual error (missing id)
    error_msg = str(exc_info.value)
    assert "id" in error_msg.lower(), f"Error should mention 'id': {error_msg}"


def test_load_includes_file_path_in_missing_text_error(tmp_path) -> None:
    """When a todo record is missing 'text', the error should include the file path."""
    db = tmp_path / "project_tasks.json"
    storage = TodoStorage(str(db))

    # Create a file with multiple records, the third one missing 'text'
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}, {"id": 3}]',
        encoding="utf-8",
    )

    # Should raise ValueError that includes the file path
    with pytest.raises(ValueError, match=r"project_tasks\.json") as exc_info:
        storage.load()

    # Also verify it still mentions the actual error (missing text)
    error_msg = str(exc_info.value)
    assert "text" in error_msg.lower(), f"Error should mention 'text': {error_msg}"


def test_load_includes_file_path_in_invalid_type_error(tmp_path) -> None:
    """When a todo record has invalid type, the error should include the file path."""
    db = tmp_path / "data.json"
    storage = TodoStorage(str(db))

    # Create a file where 'id' is a string instead of integer
    db.write_text(
        '[{"id": "not-an-integer", "text": "task"}]',
        encoding="utf-8",
    )

    # Should raise ValueError that includes the file path
    with pytest.raises(ValueError, match=r"data\.json") as exc_info:
        storage.load()

    # Also verify it still mentions the actual error (invalid id)
    error_msg = str(exc_info.value)
    assert "id" in error_msg.lower(), f"Error should mention 'id': {error_msg}"


def test_load_includes_record_index_in_error(tmp_path) -> None:
    """When a todo record has an error, the error should indicate which record."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create a file with multiple records, the second one (index 1) missing 'id'
    db.write_text(
        '[{"id": 1, "text": "valid"}, {"text": "no id"}]',
        encoding="utf-8",
    )

    # Should raise ValueError that indicates the record index
    with pytest.raises(ValueError, match=r"record.*(1|2|second)"):
        storage.load()


def test_load_valid_data_succeeds(tmp_path) -> None:
    """Valid data should load without errors."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2", "done": true}]',
        encoding="utf-8",
    )

    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].text == "task1"
    assert todos[1].done is True
