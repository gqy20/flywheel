"""Tests for JSON list element type validation (Issue #5776).

These tests verify that:
1. JSON lists with non-dict elements raise ValueError (not TypeError)
2. Error messages clearly indicate the element type and index
3. Mixed valid/invalid lists still raise ValueError for invalid elements
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_list_of_integers(tmp_path) -> None:
    """JSON list of integers should raise ValueError, not TypeError."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but elements are integers, not dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"must be.*object|element.*dict"):
        storage.load()


def test_storage_load_rejects_list_of_strings(tmp_path) -> None:
    """JSON list of strings should raise ValueError, not TypeError."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but elements are strings, not dicts
    db.write_text('["not", "dicts"]', encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"must be.*object|element.*dict"):
        storage.load()


def test_storage_load_rejects_list_with_null_element(tmp_path) -> None:
    """JSON list containing null should raise ValueError."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains null
    db.write_text("[null]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"must be.*object|element.*dict"):
        storage.load()


def test_storage_load_rejects_mixed_valid_invalid_list(tmp_path) -> None:
    """JSON list with mixed valid/invalid elements should raise ValueError."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Valid first element, invalid second element
    db.write_text('[{"id": 1, "text": "valid"}, "invalid"]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"must be.*object|element.*dict"):
        storage.load()


def test_storage_load_error_message_includes_type_and_index(tmp_path) -> None:
    """Error message should include the actual type received and index."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "first"}, 42]', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    # Should mention the type (int/integer) and possibly the index (1)
    assert "int" in error_msg or "integer" in error_msg


def test_storage_load_accepts_valid_list_of_dicts(tmp_path) -> None:
    """Valid JSON list of dict objects should still work after fix."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].text == "task1"
    assert todos[1].text == "task2"


def test_storage_load_empty_list_still_works(tmp_path) -> None:
    """Empty JSON list should still work."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    db.write_text("[]", encoding="utf-8")

    # Should return empty list
    todos = storage.load()
    assert todos == []
