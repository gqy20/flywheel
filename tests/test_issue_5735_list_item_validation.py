"""Tests for list item validation in storage.load() (Issue #5735).

These tests verify that:
1. JSON files with non-dict list items raise clear ValueError
2. Valid JSON files with dict list items continue to work
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_list_of_integers(tmp_path) -> None:
    """Issue #5735: JSON file [1, 2, 3] should raise clear ValueError, not TypeError."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with integer list items
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"must be.*JSON objects|must be.*dictionaries"):
        storage.load()


def test_storage_load_rejects_list_of_strings(tmp_path) -> None:
    """Issue #5735: JSON file with string items should raise clear ValueError."""
    db = tmp_path / "strings.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with string list items
    db.write_text('["task1", "task2"]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"must be.*JSON objects|must be.*dictionaries"):
        storage.load()


def test_storage_load_rejects_list_with_mixed_types(tmp_path) -> None:
    """Issue #5735: Mixed list with some non-dict items should raise ValueError."""
    db = tmp_path / "mixed.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with mixed types (one dict, one string)
    db.write_text('[{"id": 1, "text": "valid"}, "invalid"]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"must be.*JSON objects|must be.*dictionaries"):
        storage.load()


def test_storage_load_accepts_list_of_dicts(tmp_path) -> None:
    """Issue #5735: Valid JSON file with dict items should still work."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file with dict items
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2", "done": true}]', encoding="utf-8"
    )

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "task1"
    assert loaded[1].done is True
