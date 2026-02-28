"""Tests for JSON array item validation (Issue #6352).

These tests verify that load() validates each item in the JSON array
is a dict before passing to Todo.from_dict(). This prevents confusing
TypeError messages when JSON contains non-dict items like [1, 2, 3].
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_array_of_integers(tmp_path) -> None:
    """load() should raise ValueError (not TypeError) when JSON array contains integers.

    Issue #6352: load() must validate each item is a dict before calling Todo.from_dict().
    """
    db = tmp_path / "invalid_integers.json"
    storage = TodoStorage(str(db))

    # Create a file with a JSON array of integers (not dicts)
    db.write_text("[1, 2, 3]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"item.*0.*dict|index 0.*not.*dict"):
        storage.load()


def test_storage_load_rejects_array_with_null(tmp_path) -> None:
    """load() should raise ValueError when JSON array contains null."""
    db = tmp_path / "invalid_null.json"
    storage = TodoStorage(str(db))

    # Create a file with a JSON array containing null
    db.write_text("[null]", encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"item.*0.*dict|index 0.*not.*dict"):
        storage.load()


def test_storage_load_rejects_array_of_strings(tmp_path) -> None:
    """load() should raise ValueError when JSON array contains strings."""
    db = tmp_path / "invalid_strings.json"
    storage = TodoStorage(str(db))

    # Create a file with a JSON array of strings (not dicts)
    db.write_text('["task1", "task2"]', encoding="utf-8")

    # Should raise ValueError with clear message, not TypeError
    with pytest.raises(ValueError, match=r"item.*0.*dict|index 0.*not.*dict"):
        storage.load()


def test_storage_load_rejects_mixed_array_with_non_dict(tmp_path) -> None:
    """load() should raise ValueError when JSON array contains a mix of valid and invalid items."""
    db = tmp_path / "invalid_mixed.json"
    storage = TodoStorage(str(db))

    # Create a file with mixed valid and invalid items
    db.write_text(
        '[{"id": 1, "text": "valid"}, 42, {"id": 2, "text": "also valid"}]',
        encoding="utf-8",
    )

    # Should raise ValueError pointing to the invalid item (index 1)
    with pytest.raises(ValueError, match=r"item.*1.*dict|index 1.*not.*dict"):
        storage.load()


def test_storage_load_accepts_valid_array_of_dicts(tmp_path) -> None:
    """load() should accept a valid array of dict items."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create a file with valid JSON array of dicts
    db.write_text('[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].text == "task1"
    assert todos[1].text == "task2"
