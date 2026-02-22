"""Tests for non-dict element validation in load() (Issue #5214).

These tests verify that:
1. JSON arrays with non-dict elements produce clear error messages
2. Error messages include the index of the problematic element
3. Error messages indicate that elements must be objects/dicts
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_array_of_strings(tmp_path) -> None:
    """JSON array of strings should produce clear error message."""
    db = tmp_path / "strings.json"
    storage = TodoStorage(str(db))

    # Valid JSON array, but elements are strings, not objects
    db.write_text('["not a dict", "also not a dict"]', encoding="utf-8")

    # Should raise clear error about elements being wrong type
    with pytest.raises(ValueError, match=r"[Ee]lement.*must be.*object"):
        storage.load()


def test_storage_load_rejects_array_of_numbers(tmp_path) -> None:
    """JSON array of numbers should produce clear error message."""
    db = tmp_path / "numbers.json"
    storage = TodoStorage(str(db))

    # Valid JSON array, but elements are numbers, not objects
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise clear error about elements being wrong type
    with pytest.raises(ValueError, match=r"[Ee]lement.*must be.*object"):
        storage.load()


def test_storage_load_rejects_array_with_null_element(tmp_path) -> None:
    """JSON array with null element should produce clear error message."""
    db = tmp_path / "null_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON array, but contains null
    db.write_text('[{"id": 1, "text": "valid"}, null]', encoding="utf-8")

    # Should raise clear error about elements being wrong type
    with pytest.raises(ValueError, match=r"[Ee]lement.*must be.*object"):
        storage.load()


def test_storage_load_error_includes_element_index(tmp_path) -> None:
    """Error message should include the index of the problematic element."""
    db = tmp_path / "index_test.json"
    storage = TodoStorage(str(db))

    # Third element (index 2) is not a dict
    db.write_text(
        '[{"id": 1, "text": "valid"}, {"id": 2, "text": "also valid"}, "invalid"]',
        encoding="utf-8",
    )

    # Should include index 2 in error message
    with pytest.raises(ValueError, match=r"index 2|索引 2"):
        storage.load()


def test_storage_load_rejects_array_of_booleans(tmp_path) -> None:
    """JSON array of booleans should produce clear error message."""
    db = tmp_path / "booleans.json"
    storage = TodoStorage(str(db))

    # Valid JSON array, but elements are booleans, not objects
    db.write_text("[true, false]", encoding="utf-8")

    # Should raise clear error about elements being wrong type
    with pytest.raises(ValueError, match=r"[Ee]lement.*must be.*object"):
        storage.load()
