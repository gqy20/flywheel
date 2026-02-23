"""Regression test for issue #5352.

load() should raise a clear ValueError (not TypeError) when JSON array
contains non-dictionary elements.

Before fix: TypeError: argument of type 'int' is not iterable
After fix: ValueError with clear message indicating index and expected type
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_array_with_int_elements(tmp_path) -> None:
    """Test that load() rejects JSON array with integer elements."""
    db = tmp_path / "todo.json"
    db.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    storage = TodoStorage(str(db))

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    # Should mention the element index and expected type
    assert "index 0" in str(exc_info.value).lower()
    assert "dict" in str(exc_info.value).lower()


def test_load_rejects_array_with_string_elements(tmp_path) -> None:
    """Test that load() rejects JSON array with string elements."""
    db = tmp_path / "todo.json"
    db.write_text(json.dumps(["string"]), encoding="utf-8")

    storage = TodoStorage(str(db))

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    # Should mention the element index and expected type
    assert "index 0" in str(exc_info.value).lower()
    assert "dict" in str(exc_info.value).lower()


def test_load_rejects_array_with_mixed_invalid_elements(tmp_path) -> None:
    """Test that load() reports the correct index for invalid elements."""
    # Valid dict followed by invalid int
    db = tmp_path / "todo.json"
    db.write_text(
        json.dumps([{"id": 1, "text": "valid"}, 123]),
        encoding="utf-8",
    )

    storage = TodoStorage(str(db))

    with pytest.raises(ValueError) as exc_info:
        storage.load()

    # Should report index 1 (the second element), not index 0
    assert "index 1" in str(exc_info.value).lower()
    assert "dict" in str(exc_info.value).lower()


def test_load_accepts_valid_dict_array(tmp_path) -> None:
    """Test that load() still accepts valid JSON array of dicts."""
    db = tmp_path / "todo.json"
    db.write_text(
        json.dumps([{"id": 1, "text": "task1"}, {"id": 2, "text": "task2", "done": True}]),
        encoding="utf-8",
    )

    storage = TodoStorage(str(db))

    # Should not raise
    todos = storage.load()
    assert len(todos) == 2
    assert todos[0].text == "task1"
    assert todos[1].text == "task2"
