"""Tests for JSON decode error handling in TodoStorage.load() - Issue #1958.

This test suite verifies that TodoStorage.load() properly handles JSON parsing errors
and provides clear error messages instead of crashing with raw json.JSONDecodeError.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_handles_malformed_json(tmp_path) -> None:
    """Test that load() raises ValueError with clear message for malformed JSON."""
    db = tmp_path / "corrupted.json"
    storage = TodoStorage(str(db))

    # Create a file with invalid JSON syntax
    db.write_text('{"invalid": }', encoding="utf-8")

    # Should raise ValueError with clear message, not raw json.JSONDecodeError
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value)
    # Error message should contain file path for debugging
    assert str(db) in error_msg or "corrupted.json" in error_msg
    # Error message should mention parsing failure
    assert "parse" in error_msg.lower() or "json" in error_msg.lower()


def test_load_handles_non_list_json(tmp_path) -> None:
    """Test that load() raises ValueError for valid JSON that is not a list."""
    db = tmp_path / "not-a-list.json"
    storage = TodoStorage(str(db))

    # Create a file with valid JSON but not a list (e.g., a dict)
    db.write_text('{"todo": "item"}', encoding="utf-8")

    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value)
    # Error message should mention the type mismatch
    assert "list" in error_msg.lower()


def test_load_handles_trailing_comma_json(tmp_path) -> None:
    """Test handling of JSON with trailing comma (common corruption pattern)."""
    db = tmp_path / "trailing-comma.json"
    storage = TodoStorage(str(db))

    # JSON with trailing comma is invalid (common corruption)
    db.write_text('[{"id": 1, "text": "task"},]', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value)
    assert "parse" in error_msg.lower() or "json" in error_msg.lower()


def test_load_handles_unclosed_string_json(tmp_path) -> None:
    """Test handling of JSON with unclosed string."""
    db = tmp_path / "unclosed-string.json"
    storage = TodoStorage(str(db))

    # JSON with unclosed string
    db.write_text('[{"id": 1, "text": "task}]', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value)
    assert "parse" in error_msg.lower() or "json" in error_msg.lower()


def test_load_error_message_includes_file_path(tmp_path) -> None:
    """Test that error messages include the actual file path for debugging."""
    db = tmp_path / "my-todos.json"
    storage = TodoStorage(str(db))

    db.write_text('broken json{', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value)
    # File path should be in error message
    assert "my-todos.json" in error_msg


def test_load_empty_file_returns_empty_list(tmp_path) -> None:
    """Test that an empty file (valid empty JSON array) returns empty list."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Empty JSON array is valid
    db.write_text('[]', encoding="utf-8")

    result = storage.load()
    assert result == []


def test_load_whitespace_only_file_is_handled(tmp_path) -> None:
    """Test that a file with only whitespace is handled gracefully."""
    db = tmp_path / "whitespace.json"
    storage = TodoStorage(str(db))

    # File with only whitespace is not valid JSON
    db.write_text('   \n\t  ', encoding="utf-8")

    with pytest.raises(ValueError):
        storage.load()
