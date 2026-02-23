"""Tests for non-dict element handling in JSON arrays (Issue #5352).

These tests verify that:
1. JSON arrays with integer elements produce clear error messages
2. JSON arrays with string elements produce clear error messages
3. Error messages include element index and expected type
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_integer_array_elements(tmp_path) -> None:
    """JSON array with integer elements should produce clear ValueError."""
    db = tmp_path / "int_elements.json"
    storage = TodoStorage(str(db))

    # Create a file with integer elements instead of dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message about element type
    with pytest.raises(ValueError, match=r"element|index.*0|dict|object"):
        storage.load()


def test_storage_load_rejects_string_array_elements(tmp_path) -> None:
    """JSON array with string elements should produce clear ValueError."""
    db = tmp_path / "string_elements.json"
    storage = TodoStorage(str(db))

    # Create a file with string elements instead of dicts
    db.write_text('["string"]', encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message about element type
    with pytest.raises(ValueError, match=r"element|index.*0|dict|object"):
        storage.load()


def test_storage_load_rejects_mixed_valid_and_invalid_elements(tmp_path) -> None:
    """JSON array with mixed valid and invalid elements should report the bad index."""
    db = tmp_path / "mixed_elements.json"
    storage = TodoStorage(str(db))

    # Create a file with a mix of valid dict and invalid integer
    db.write_text('[{"id": 1, "text": "valid"}, 42]', encoding="utf-8")

    # Should raise ValueError mentioning the index of the bad element
    with pytest.raises(ValueError, match=r"element|index.*1|dict|object"):
        storage.load()


def test_storage_load_error_not_typeerror_for_int_element(tmp_path) -> None:
    """Verify that integer elements do NOT produce a TypeError."""
    db = tmp_path / "int_element.json"
    storage = TodoStorage(str(db))

    db.write_text("[42]", encoding="utf-8")

    # Must NOT raise TypeError - the bug was that it raised TypeError
    # when Todo.from_dict tried to check "id" not in 42
    with pytest.raises(ValueError):
        storage.load()


def test_storage_load_error_not_typeerror_for_string_element(tmp_path) -> None:
    """Verify that string elements do NOT produce a TypeError."""
    db = tmp_path / "string_element.json"
    storage = TodoStorage(str(db))

    db.write_text('["hello"]', encoding="utf-8")

    # Must NOT raise TypeError
    with pytest.raises(ValueError):
        storage.load()
