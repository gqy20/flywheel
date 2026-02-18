"""Tests for duplicate todo ID validation (Issue #4285).

These tests verify that:
1. storage.load() raises ValueError when JSON contains duplicate IDs
2. Error message includes the duplicate ID value
3. Normal files without duplicates load successfully
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_duplicate_ids(tmp_path) -> None:
    """storage.load() should raise ValueError when JSON contains duplicate IDs."""
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Create a file with duplicate IDs
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 1, "text": "duplicate task"}]',
        encoding="utf-8",
    )

    # Should raise clear error about duplicate ID
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id|duplicate.*1"):
        storage.load()


def test_storage_load_duplicate_id_includes_id_in_error_message(tmp_path) -> None:
    """Error message should include the duplicate ID value."""
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Create a file with duplicate ID 42
    db.write_text(
        '[{"id": 42, "text": "task1"}, {"id": 42, "text": "duplicate task"}]',
        encoding="utf-8",
    )

    # Error message should contain the duplicate ID value (42)
    with pytest.raises(ValueError, match=r"42"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """Normal files without duplicates should load successfully."""
    db = tmp_path / "unique_ids.json"
    storage = TodoStorage(str(db))

    # Create a file with unique IDs
    db.write_text(
        '[{"id": 1, "text": "task1"}, {"id": 2, "text": "task2"}, {"id": 3, "text": "task3"}]',
        encoding="utf-8",
    )

    # Should load successfully without error
    todos = storage.load()
    assert len(todos) == 3
    assert todos[0].id == 1
    assert todos[1].id == 2
    assert todos[2].id == 3


def test_storage_load_duplicate_ids_multiple_occurrences(tmp_path) -> None:
    """Should detect duplicate IDs when ID appears more than twice."""
    db = tmp_path / "multiple_duplicates.json"
    storage = TodoStorage(str(db))

    # Create a file with ID 1 appearing three times
    db.write_text(
        '[{"id": 1, "text": "a"}, {"id": 1, "text": "b"}, {"id": 1, "text": "c"}]',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"(?i)duplicate.*id"):
        storage.load()


def test_storage_load_empty_file_works(tmp_path) -> None:
    """Empty file (no todos) should work fine."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    db.write_text("[]", encoding="utf-8")

    todos = storage.load()
    assert todos == []


def test_storage_load_single_item_works(tmp_path) -> None:
    """Single item (no chance of duplicate) should work fine."""
    db = tmp_path / "single.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "only task"}]', encoding="utf-8")

    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].id == 1
    assert todos[0].text == "only task"
