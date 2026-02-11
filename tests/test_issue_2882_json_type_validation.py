"""Regression test for issue #2882.

TodoStorage.load() should raise clear errors for unexpected top-level JSON values
(dict, string, number, boolean, null) instead of silently failing or iterating
over dict keys.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage


def test_load_fails_on_top_level_dict(tmp_path: Path) -> None:
    """Test that loading a JSON file with top-level dict raises ValueError."""
    db = tmp_path / "todo.json"

    # Write a top-level dict with "items" key (common mistake)
    invalid_data = {"items": [{"id": 1, "text": "example"}]}
    db.write_text(json.dumps(invalid_data), encoding="utf-8")

    storage = TodoStorage(str(db))

    # Should raise a clear error, not iterate over dict keys
    with pytest.raises(ValueError, match=r"must be a JSON list, got dict"):
        storage.load()


def test_load_fails_on_top_level_string(tmp_path: Path) -> None:
    """Test that loading a JSON file with top-level string raises ValueError."""
    db = tmp_path / "todo.json"

    # Write a top-level string
    db.write_text('"not a list"', encoding="utf-8")

    storage = TodoStorage(str(db))

    # Should raise a clear error with actual type
    with pytest.raises(ValueError, match=r"must be a JSON list, got str"):
        storage.load()


def test_load_fails_on_top_level_number(tmp_path: Path) -> None:
    """Test that loading a JSON file with top-level number raises ValueError."""
    db = tmp_path / "todo.json"

    # Write a top-level number
    db.write_text('42', encoding="utf-8")

    storage = TodoStorage(str(db))

    # Should raise a clear error with actual type
    with pytest.raises(ValueError, match=r"must be a JSON list, got int"):
        storage.load()


def test_load_fails_on_top_level_boolean(tmp_path: Path) -> None:
    """Test that loading a JSON file with top-level boolean raises ValueError."""
    db = tmp_path / "todo.json"

    # Write a top-level boolean
    db.write_text('true', encoding="utf-8")

    storage = TodoStorage(str(db))

    # Should raise a clear error with actual type
    with pytest.raises(ValueError, match=r"must be a JSON list, got bool"):
        storage.load()


def test_load_fails_on_top_level_null(tmp_path: Path) -> None:
    """Test that loading a JSON file with top-level null raises ValueError."""
    db = tmp_path / "todo.json"

    # Write a top-level null
    db.write_text('null', encoding="utf-8")

    storage = TodoStorage(str(db))

    # Should raise a clear error with actual type
    with pytest.raises(ValueError, match=r"must be a JSON list, got NoneType"):
        storage.load()


def test_load_works_on_valid_list(tmp_path: Path) -> None:
    """Test that loading a valid JSON list still works (regression check)."""
    db = tmp_path / "todo.json"

    # Write a valid list
    valid_data = [{"id": 1, "text": "example"}]
    db.write_text(json.dumps(valid_data), encoding="utf-8")

    storage = TodoStorage(str(db))

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "example"
