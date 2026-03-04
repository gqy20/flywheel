"""Tests for JSON list element type validation (Issue #7273).

These tests verify that the load() method validates that each element
in the JSON list is a dictionary before passing to Todo.from_dict().

Without this validation, malformed JSON like ["string", 123, null] would
cause TypeError instead of a clear ValueError with actionable message.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_string_list_element(tmp_path) -> None:
    """load() should reject JSON list containing a string element."""
    db = tmp_path / "string_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains a string instead of dict
    db.write_text('["not a dict"]', encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"expected an object|must be a.*dict|invalid.*element"):
        storage.load()


def test_storage_load_rejects_integer_list_element(tmp_path) -> None:
    """load() should reject JSON list containing an integer element."""
    db = tmp_path / "int_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains an integer instead of dict
    db.write_text("[123]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"expected an object|must be a.*dict|invalid.*element"):
        storage.load()


def test_storage_load_rejects_null_list_element(tmp_path) -> None:
    """load() should reject JSON list containing a null element."""
    db = tmp_path / "null_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains null instead of dict
    db.write_text("[null]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"expected an object|must be a.*dict|invalid.*element"):
        storage.load()


def test_storage_load_rejects_nested_list_element(tmp_path) -> None:
    """load() should reject JSON list containing a nested list element."""
    db = tmp_path / "nested_list.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains a nested list instead of dict
    db.write_text("[[1, 2, 3]]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"expected an object|must be a.*dict|invalid.*element"):
        storage.load()


def test_storage_load_rejects_mixed_invalid_elements(tmp_path) -> None:
    """load() should reject JSON list with mixed valid/invalid elements."""
    db = tmp_path / "mixed.json"
    storage = TodoStorage(str(db))

    # JSON list with one valid dict and one invalid string element
    db.write_text('[{"id": 1, "text": "valid"}, "invalid"]', encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"expected an object|must be a.*dict|invalid.*element"):
        storage.load()
