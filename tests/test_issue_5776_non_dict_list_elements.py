"""Tests for JSON list element type validation (Issue #5776).

These tests verify that:
1. When JSON list contains non-dict elements, ValueError is raised (not TypeError)
2. Error message clearly indicates that list elements must be objects/dicts
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_list_of_integers(tmp_path) -> None:
    """When JSON list contains integers, ValueError should be raised, not TypeError."""
    db = tmp_path / "invalid_elements.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with integer elements instead of dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"list element|must be.*dict|must be.*object"):
        storage.load()


def test_load_rejects_list_of_strings(tmp_path) -> None:
    """When JSON list contains strings, ValueError should be raised, not TypeError."""
    db = tmp_path / "string_elements.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with string elements instead of dicts
    db.write_text('["task1", "task2"]', encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"list element|must be.*dict|must be.*object"):
        storage.load()


def test_load_rejects_mixed_valid_and_invalid_elements(tmp_path) -> None:
    """When JSON list contains mix of dict and non-dict, ValueError should be raised."""
    db = tmp_path / "mixed_elements.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with mixed elements
    db.write_text('[{"id": 1, "text": "valid"}, 123]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"list element|must be.*dict|must be.*object"):
        storage.load()


def test_load_rejects_list_of_nulls(tmp_path) -> None:
    """When JSON list contains null values, ValueError should be raised."""
    db = tmp_path / "null_elements.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with null elements
    db.write_text("[null, null]", encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"list element|must be.*dict|must be.*object"):
        storage.load()


def test_load_accepts_valid_dict_elements(tmp_path) -> None:
    """Valid dict elements should still load correctly after validation is added."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].text == "task1"
    assert todos[1].text == "task2"
