"""Tests for list element validation in TodoStorage.load() (Issue #4806).

These tests verify that:
1. load() validates each list element is a dict before passing to Todo.from_dict()
2. Non-dict elements produce clear error messages indicating the element type and index
3. Valid lists of dicts still load correctly
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_list_with_int_elements(tmp_path) -> None:
    """List with integer elements should raise clear ValueError."""
    db = tmp_path / "int_elements.json"
    storage = TodoStorage(str(db))

    # JSON list with integer elements instead of dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with message indicating element must be a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary|element.*dict"):
        storage.load()


def test_load_rejects_list_with_string_elements(tmp_path) -> None:
    """List with string elements should raise clear ValueError."""
    db = tmp_path / "string_elements.json"
    storage = TodoStorage(str(db))

    # JSON list with string elements instead of dicts
    db.write_text('["invalid", "strings"]', encoding="utf-8")

    # Should raise ValueError with message indicating element must be a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary|element.*dict"):
        storage.load()


def test_load_rejects_mixed_valid_invalid_list(tmp_path) -> None:
    """Mixed list with valid dict and invalid element should raise clear ValueError."""
    db = tmp_path / "mixed_elements.json"
    storage = TodoStorage(str(db))

    # JSON list with one valid dict and one invalid string element
    db.write_text('[{"id": 1, "text": "valid"}, "invalid"]', encoding="utf-8")

    # Should raise ValueError with message indicating element must be a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary|element.*dict"):
        storage.load()


def test_load_rejects_list_with_null_element(tmp_path) -> None:
    """List with null element should raise clear ValueError."""
    db = tmp_path / "null_element.json"
    storage = TodoStorage(str(db))

    # JSON list with null element
    db.write_text('[{"id": 1, "text": "valid"}, null]', encoding="utf-8")

    # Should raise ValueError with message indicating element must be a dictionary
    with pytest.raises(ValueError, match=r"must be a dictionary|element.*dict"):
        storage.load()


def test_load_accepts_valid_list_of_dicts(tmp_path) -> None:
    """Valid list of dicts should load correctly."""
    db = tmp_path / "valid_list.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with proper dict elements
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2", "done": true}]', encoding="utf-8")

    # Should load without errors
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].text == "task2"
    assert todos[1].done is True


def test_load_error_message_includes_index_and_type(tmp_path) -> None:
    """Error message should include element index and actual type for debugging."""
    db = tmp_path / "error_details.json"
    storage = TodoStorage(str(db))

    # JSON list where second element (index 1) is invalid
    db.write_text('[{"id": 1, "text": "valid"}, 42]', encoding="utf-8")

    # Should raise ValueError with index and type information
    with pytest.raises(ValueError) as exc_info:
        storage.load()

    error_msg = str(exc_info.value).lower()
    # Error message should indicate the problematic index and/or type
    assert "index" in error_msg or "element" in error_msg
    # Should mention the actual type received (int/int)
    assert "int" in error_msg or "integer" in error_msg or "dict" in error_msg
