"""Regression test for issue #1958: JSON parse error handling in TodoStorage.load().

This test suite verifies that TodoStorage.load() properly handles JSON parsing errors
and provides clear, actionable error messages when the JSON file is corrupted.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_with_invalid_json_raises_clear_error(tmp_path) -> None:
    """Test that malformed JSON raises a clear ValueError with file path.

    Regression test for issue #1958: When a JSON file is corrupted,
    the program should raise ValueError with a helpful error message
    instead of crashing with raw json.JSONDecodeError.
    """
    db = tmp_path / "corrupted.json"
    storage = TodoStorage(str(db))

    # Write corrupted JSON (missing closing bracket)
    db.write_text('[{"id": 1, "text": "task1"}', encoding="utf-8")

    # Should raise ValueError (not JSONDecodeError) with clear message
    with pytest.raises(ValueError, match="Failed to parse todo file"):
        storage.load()


def test_load_with_non_list_json_raises_value_error(tmp_path) -> None:
    """Test that valid JSON but wrong type (not a list) raises ValueError.

    Even if the JSON is syntactically valid, if it's not a list,
    we should raise a clear ValueError.
    """
    db = tmp_path / "wrong_type.json"
    storage = TodoStorage(str(db))

    # Write valid JSON but wrong type (object instead of list)
    db.write_text('{"id": 1, "text": "task1"}', encoding="utf-8")

    # Should raise ValueError with clear message about type
    with pytest.raises(ValueError, match="Todo storage must be a JSON list"):
        storage.load()


def test_load_error_message_contains_file_path(tmp_path) -> None:
    """Test that error message includes the problematic file path.

    The error message should help users identify which file is corrupted.
    """
    db = tmp_path / "specific_file.json"
    storage = TodoStorage(str(db))

    # Write corrupted JSON with trailing comma (invalid)
    db.write_text('[{"id": 1, "text": "task1",}]', encoding="utf-8")

    # Error message should contain the file path
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value)
    assert "specific_file.json" in error_msg
    assert "Failed to parse todo file" in error_msg


def test_load_with_empty_file_raises_clear_error(tmp_path) -> None:
    """Test that empty file raises a clear error.

    An empty file is technically valid JSON but produces None,
    which should be handled gracefully.
    """
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Write empty file
    db.write_text("", encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match="Failed to parse todo file"):
        storage.load()


def test_load_with_json_dict_instead_of_list(tmp_path) -> None:
    """Test that a JSON dict (not list) raises appropriate error."""
    db = tmp_path / "dict.json"
    storage = TodoStorage(str(db))

    # Write a dict instead of list
    db.write_text('{"task": "value"}', encoding="utf-8")

    # Should raise ValueError about needing a list
    with pytest.raises(ValueError, match="Todo storage must be a JSON list"):
        storage.load()


def test_load_with_json_number_instead_of_list(tmp_path) -> None:
    """Test that a JSON number (not list) raises appropriate error."""
    db = tmp_path / "number.json"
    storage = TodoStorage(str(db))

    # Write a number instead of list
    db.write_text("42", encoding="utf-8")

    # Should raise ValueError about needing a list
    with pytest.raises(ValueError, match="Todo storage must be a JSON list"):
        storage.load()


def test_load_with_trailing_garbage(tmp_path) -> None:
    """Test that JSON with trailing garbage raises a clear error."""
    db = tmp_path / "garbage.json"
    storage = TodoStorage(str(db))

    # Write valid JSON followed by garbage
    db.write_text("[] trailing garbage", encoding="utf-8")

    # Should raise ValueError with parse error message
    with pytest.raises(ValueError, match="Failed to parse todo file"):
        storage.load()


def test_load_valid_json_still_works(tmp_path) -> None:
    """Test that valid JSON still loads correctly (no regression)."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Write valid JSON
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2", done=True)]
    storage.save(todos)

    # Should load without issues
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "task1"
    assert loaded[1].text == "task2"
    assert loaded[1].done is True


def test_load_nonexistent_file_returns_empty_list(tmp_path) -> None:
    """Test that nonexistent file returns empty list (no regression)."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File doesn't exist, should return empty list
    loaded = storage.load()
    assert loaded == []
