"""Tests for JSON list element type validation (Issue #7273).

These tests verify that the load() method validates that each element
in the JSON list is a dict before passing to Todo.from_dict().
This prevents confusing TypeError when JSON contains non-dict elements.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_null_element(tmp_path) -> None:
    """JSON file containing [null] should raise ValueError, not TypeError."""
    db = tmp_path / "null_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains null element
    db.write_text("[null]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"element.*dict|invalid.*element|must be.*dict"):
        storage.load()


def test_storage_load_rejects_string_element(tmp_path) -> None:
    """JSON file containing ["string"] should raise ValueError."""
    db = tmp_path / "string_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains string element
    db.write_text('["not a dict"]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"element.*dict|invalid.*element|must be.*dict"):
        storage.load()


def test_storage_load_rejects_number_element(tmp_path) -> None:
    """JSON file containing [1, 2, 3] should raise ValueError."""
    db = tmp_path / "number_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains number elements
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"element.*dict|invalid.*element|must be.*dict"):
        storage.load()


def test_storage_load_rejects_mixed_valid_and_null_element(tmp_path) -> None:
    """JSON file with valid todo followed by null should raise ValueError with position info."""
    db = tmp_path / "mixed_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with valid todo followed by null
    db.write_text('[{"id": 1, "text": "valid"}, null]', encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError, match=r"element.*dict|invalid.*element|must be.*dict"):
        storage.load()


def test_storage_load_accepts_valid_list_of_dicts(tmp_path) -> None:
    """JSON file with valid list of dicts should load successfully."""
    db = tmp_path / "valid_todos.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with valid todo objects
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].text == "task1"
    assert todos[1].text == "task2"
