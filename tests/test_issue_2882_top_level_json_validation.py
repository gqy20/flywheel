"""Regression test for issue #2882: TodoStorage.load() should reject non-list top-level JSON.

This test verifies that:
1. Loading a JSON file with top-level object (dict) produces clear error message
2. Loading a JSON file with top-level string, number, boolean, null produces clear error message
3. The error message includes the actual type found for better debugging
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage


def test_storage_load_rejects_top_level_dict(tmp_path) -> None:
    """Bug #2882: Loading a JSON file with top-level dict should raise clear error."""
    db = tmp_path / "dict.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with top-level object (dict)
    db.write_text('{"items": [{"id": 1, "text": "task"}]}', encoding="utf-8")

    # Should raise ValueError with clear message mentioning actual type (dict)
    with pytest.raises(ValueError, match=r"must be a JSON list.*dict|got dict"):
        storage.load()


def test_storage_load_rejects_top_level_string(tmp_path) -> None:
    """Bug #2882: Loading a JSON file with top-level string should raise clear error."""
    db = tmp_path / "string.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with top-level string
    db.write_text('"not a list"', encoding="utf-8")

    # Should raise ValueError with clear message mentioning the actual type (str)
    with pytest.raises(ValueError, match=r"must be a JSON list.*str|got str"):
        storage.load()


def test_storage_load_rejects_top_level_number(tmp_path) -> None:
    """Bug #2882: Loading a JSON file with top-level number should raise clear error."""
    db = tmp_path / "number.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with top-level number
    db.write_text('42', encoding="utf-8")

    # Should raise ValueError with clear message mentioning the actual type (int)
    with pytest.raises(ValueError, match=r"must be a JSON list.*int|got int"):
        storage.load()


def test_storage_load_rejects_top_level_boolean(tmp_path) -> None:
    """Bug #2882: Loading a JSON file with top-level boolean should raise clear error."""
    db = tmp_path / "bool.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with top-level boolean
    db.write_text('true', encoding="utf-8")

    # Should raise ValueError with clear message mentioning the actual type (bool)
    with pytest.raises(ValueError, match=r"must be a JSON list.*bool|got bool"):
        storage.load()


def test_storage_load_rejects_top_level_null(tmp_path) -> None:
    """Bug #2882: Loading a JSON file with top-level null should raise clear error."""
    db = tmp_path / "null.json"
    storage = TodoStorage(str(db))

    # Create a JSON file with top-level null
    db.write_text('null', encoding="utf-8")

    # Should raise ValueError with clear message mentioning the actual type (NoneType)
    with pytest.raises(ValueError, match=r"must be a JSON list.*None|got None"):
        storage.load()


def test_storage_load_accepts_valid_list(tmp_path) -> None:
    """Bug #2882: Verify existing list-based test still passes."""
    db = tmp_path / "valid.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file with top-level list
    db.write_text('[{"id": 1, "text": "task"}]', encoding="utf-8")

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "task"
