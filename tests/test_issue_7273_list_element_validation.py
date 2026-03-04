"""Tests for JSON list element type validation (Issue #7273).

These tests verify that load() validates each element in the JSON list
is a dict before passing to Todo.from_dict(), preventing confusing TypeErrors.

Security: Malformed JSON data with non-dict list elements should produce
clear ValueError messages, not cryptic TypeError/KeyError.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_null_in_list(tmp_path) -> None:
    """JSON list with null element should raise clear ValueError, not TypeError."""
    db = tmp_path / "null_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains null instead of dict
    db.write_text("[null]", encoding="utf-8")

    # Should raise ValueError with clear message about element type
    with pytest.raises(ValueError, match=r"element.*dict|dict.*expected|must be.*dict"):
        storage.load()


def test_storage_load_rejects_string_in_list(tmp_path) -> None:
    """JSON list with string element should raise clear ValueError."""
    db = tmp_path / "string_element.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains string instead of dict
    db.write_text('["string"]', encoding="utf-8")

    # Should raise ValueError with clear message about element type
    with pytest.raises(ValueError, match=r"element.*dict|dict.*expected|must be.*dict"):
        storage.load()


def test_storage_load_rejects_integer_list(tmp_path) -> None:
    """JSON list with integers should raise clear ValueError."""
    db = tmp_path / "int_list.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains integers instead of dicts
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with clear message about element type
    with pytest.raises(ValueError, match=r"element.*dict|dict.*expected|must be.*dict"):
        storage.load()


def test_storage_load_rejects_mixed_valid_and_null(tmp_path) -> None:
    """JSON list with valid todo followed by null should raise ValueError with index."""
    db = tmp_path / "mixed.json"
    storage = TodoStorage(str(db))

    # First element is valid, second is null
    db.write_text('[{"id": 1, "text": "valid"}, null]', encoding="utf-8")

    # Should raise ValueError mentioning the element index
    with pytest.raises(ValueError, match=r"element.*1|index.*1|position.*1|dict"):
        storage.load()


def test_storage_load_rejects_nested_list_in_list(tmp_path) -> None:
    """JSON list with nested list element should raise clear ValueError."""
    db = tmp_path / "nested_list.json"
    storage = TodoStorage(str(db))

    # Valid JSON list but contains nested list instead of dict
    db.write_text('[["nested", "list"]]', encoding="utf-8")

    # Should raise ValueError with clear message about element type
    with pytest.raises(ValueError, match=r"element.*dict|dict.*expected|must be.*dict"):
        storage.load()


def test_storage_load_accepts_valid_list_of_dicts(tmp_path) -> None:
    """Valid JSON list with proper dict elements should load successfully."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Valid JSON list with proper todo objects
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[0].text == "task1"
    assert todos[1].id == 2
    assert todos[1].text == "task2"
