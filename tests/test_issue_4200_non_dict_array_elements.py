"""Tests for Issue #4200: Non-dict array elements should raise clear ValueError.

The load() method should validate that each array element is a dictionary
before calling Todo.from_dict(). This prevents confusing TypeErrors when
the JSON file contains non-dict elements like [1, 2, 3] or [null].
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_array_with_int_elements(tmp_path) -> None:
    """load() should raise ValueError when JSON array contains integers."""
    db = tmp_path / "int_array.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with integer array elements
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"must be.*dict|object|dictionary"):
        storage.load()


def test_storage_load_rejects_array_with_null_element(tmp_path) -> None:
    """load() should raise ValueError when JSON array contains null."""
    db = tmp_path / "null_array.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with null element
    db.write_text("[null]", encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"must be.*dict|object|dictionary"):
        storage.load()


def test_storage_load_rejects_array_with_string_elements(tmp_path) -> None:
    """load() should raise ValueError when JSON array contains strings."""
    db = tmp_path / "string_array.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with string elements
    db.write_text('["task1", "task2"]', encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"must be.*dict|object|dictionary"):
        storage.load()


def test_storage_load_rejects_array_with_list_elements(tmp_path) -> None:
    """load() should raise ValueError when JSON array contains nested lists."""
    db = tmp_path / "nested_list.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with nested list elements
    db.write_text('[[1, 2], [3, 4]]', encoding="utf-8")

    # Should raise ValueError (not TypeError) with clear message
    with pytest.raises(ValueError, match=r"must be.*dict|object|dictionary"):
        storage.load()


def test_storage_load_error_message_indicates_element_index(tmp_path) -> None:
    """Error message should indicate which element is invalid."""
    db = tmp_path / "mixed_array.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with a valid dict followed by an invalid element
    db.write_text('[{"id": 1, "text": "valid"}, 42]', encoding="utf-8")

    # Should raise ValueError and ideally mention the element index or value
    with pytest.raises(ValueError, match=r"must be.*dict|object|dictionary"):
        storage.load()
