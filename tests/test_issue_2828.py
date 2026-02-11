"""Tests for Todo.from_dict timestamp field validation (Issue #2828).

These tests verify that:
1. created_at/updated_at fields reject invalid types (dict, list, etc.)
2. created_at/updated_at fields accept None and use empty string default
3. created_at/updated_at fields accept valid ISO timestamp strings
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_dict_for_created_at() -> None:
    """from_dict should reject dict values for created_at field."""
    with pytest.raises(ValueError, match=r"created_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "created_at": {}})


def test_from_dict_rejects_list_for_created_at() -> None:
    """from_dict should reject list values for created_at field."""
    with pytest.raises(ValueError, match=r"created_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "created_at": []})


def test_from_dict_rejects_dict_for_updated_at() -> None:
    """from_dict should reject dict values for updated_at field."""
    with pytest.raises(ValueError, match=r"updated_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "updated_at": {"key": "value"}})


def test_from_dict_rejects_list_for_updated_at() -> None:
    """from_dict should reject list values for updated_at field."""
    with pytest.raises(ValueError, match=r"updated_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "updated_at": [1, 2, 3]})


def test_from_dict_accepts_none_for_created_at() -> None:
    """from_dict should accept None for created_at (defaults to current time via __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})
    # None becomes "" which triggers __post_init__ to set current ISO time
    assert todo.created_at != ""
    assert "T" in todo.created_at  # Basic ISO format check


def test_from_dict_accepts_none_for_updated_at() -> None:
    """from_dict should accept None for updated_at (defaults to created_at via __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": None})
    # None becomes "" which triggers __post_init__ to copy created_at
    assert todo.updated_at != ""
    assert "T" in todo.updated_at  # Basic ISO format check


def test_from_dict_accepts_valid_iso_string() -> None:
    """from_dict should accept valid ISO timestamp strings."""
    iso_time = "2024-01-01T00:00:00+00:00"
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": iso_time,
        "updated_at": iso_time,
    })
    assert todo.created_at == iso_time
    assert todo.updated_at == iso_time


def test_from_dict_omits_created_at_gracefully() -> None:
    """from_dict should handle missing created_at field gracefully."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    # Missing field should result in empty string which triggers __post_init__
    assert todo.created_at != ""  # __post_init__ sets it to current ISO time


def test_from_dict_omits_updated_at_gracefully() -> None:
    """from_dict should handle missing updated_at field gracefully."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    # Missing field should result in empty string which triggers __post_init__
    assert todo.updated_at != ""  # __post_init__ sets it to created_at value


def test_from_dict_accepts_numeric_timestamps_as_string() -> None:
    """from_dict should accept numeric timestamps if they are strings."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "1704067200",
        "updated_at": "1704067200",
    })
    assert todo.created_at == "1704067200"
    assert todo.updated_at == "1704067200"


def test_from_dict_rejects_int_for_created_at() -> None:
    """from_dict should reject int values for created_at field."""
    with pytest.raises(ValueError, match=r"created_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "created_at": 1704067200})


def test_from_dict_rejects_float_for_updated_at() -> None:
    """from_dict should reject float values for updated_at field."""
    with pytest.raises(ValueError, match=r"updated_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "updated_at": 1704067200.5})


def test_from_dict_to_dict_roundtrip_with_valid_timestamps() -> None:
    """to_dict/from_dict roundtrip should preserve valid timestamps."""
    original = Todo(id=1, text="test")
    original_dict = original.to_dict()
    restored = Todo.from_dict(original_dict)
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
    assert isinstance(restored.created_at, str)
    assert isinstance(restored.updated_at, str)
