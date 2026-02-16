"""Tests for duplicate ID validation in storage.load() (Issue #3762).

These tests verify that:
1. Loading a JSON file with duplicate IDs produces a clear error message
2. This prevents silent data corruption where next_id would break
3. Users get clear feedback about which IDs are duplicated
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_duplicate_ids(tmp_path) -> None:
    """storage.load() should reject JSON files with duplicate IDs."""
    db = tmp_path / "duplicate_ids.json"
    storage = TodoStorage(str(db))

    # Valid JSON but with duplicate IDs (both have id=1)
    db.write_text(
        '[{"id": 1, "text": "first task"}, {"id": 1, "text": "second task"}]',
        encoding="utf-8",
    )

    # Should raise ValueError with clear message about duplicate IDs
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id"):
        storage.load()


def test_storage_load_rejects_multiple_duplicate_ids(tmp_path) -> None:
    """storage.load() should report when multiple IDs are duplicated."""
    db = tmp_path / "multiple_duplicates.json"
    storage = TodoStorage(str(db))

    # Valid JSON but with multiple duplicate IDs (id=1 appears 3 times, id=2 appears 2 times)
    db.write_text(
        '[{"id": 1, "text": "a"}, {"id": 2, "text": "b"}, {"id": 1, "text": "c"}, '
        '{"id": 2, "text": "d"}, {"id": 1, "text": "e"}]',
        encoding="utf-8",
    )

    # Should raise ValueError mentioning duplicate IDs
    with pytest.raises(ValueError, match=r"(?i)duplicate.*id"):
        storage.load()


def test_storage_load_accepts_unique_ids(tmp_path) -> None:
    """storage.load() should accept JSON files with unique IDs."""
    db = tmp_path / "unique_ids.json"
    storage = TodoStorage(str(db))

    # Valid JSON with unique IDs
    db.write_text(
        '[{"id": 1, "text": "first task"}, {"id": 2, "text": "second task"}]',
        encoding="utf-8",
    )

    # Should load successfully without errors
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].id == 1
    assert todos[1].id == 2


def test_storage_load_empty_list_succeeds(tmp_path) -> None:
    """storage.load() should accept empty JSON list."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    db.write_text("[]", encoding="utf-8")

    # Should load successfully with empty list
    todos = storage.load()
    assert len(todos) == 0


def test_storage_load_single_item_succeeds(tmp_path) -> None:
    """storage.load() should accept single item with no duplicates."""
    db = tmp_path / "single.json"
    storage = TodoStorage(str(db))

    db.write_text('[{"id": 1, "text": "only task"}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].id == 1
