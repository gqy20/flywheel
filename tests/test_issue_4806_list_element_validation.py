"""Tests for list element validation in load() (Issue #4806).

These tests verify that:
1. load() validates each list element is a dict before passing to from_dict
2. Clear error message is provided when list element is not a dict
3. Valid JSON list with proper dict elements still loads correctly
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_list_of_integers(tmp_path) -> None:
    """load() should reject JSON list of integers with clear error message."""
    db = tmp_path / "int_list.json"
    storage = TodoStorage(str(db))

    # JSON is a list but elements are integers, not dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with message indicating element must be a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary"):
        storage.load()


def test_storage_load_rejects_list_with_mixed_valid_invalid(tmp_path) -> None:
    """load() should reject list with valid dict followed by invalid element."""
    db = tmp_path / "mixed_list.json"
    storage = TodoStorage(str(db))

    # Valid dict followed by an invalid string element
    db.write_text('[{"id": 1, "text": "x"}, "invalid"]', encoding="utf-8")

    # Should raise ValueError with message indicating element must be a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary"):
        storage.load()


def test_storage_load_rejects_list_of_strings(tmp_path) -> None:
    """load() should reject JSON list of strings with clear error message."""
    db = tmp_path / "string_list.json"
    storage = TodoStorage(str(db))

    # JSON is a list of strings
    db.write_text('["a", "b", "c"]', encoding="utf-8")

    # Should raise ValueError with message indicating element must be a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary"):
        storage.load()


def test_storage_load_accepts_valid_list_of_dicts(tmp_path) -> None:
    """load() should accept valid JSON list of dicts."""
    db = tmp_path / "valid_list.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with proper todo dicts
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].text == "task2"
