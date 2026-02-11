"""Tests for Todo.from_dict timestamp type validation (Issue #2868).

These tests verify that:
1. from_dict rejects non-string timestamp values (int, bool, list, dict)
2. from_dict accepts valid ISO format strings
3. from_dict accepts empty strings (backward compatibility)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_int_timestamp() -> None:
    """from_dict should reject int values for created_at/updated_at."""
    with pytest.raises(ValueError, match="must be a string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 123})


def test_from_dict_rejects_int_timestamp_updated_at() -> None:
    """from_dict should reject int values for updated_at."""
    with pytest.raises(ValueError, match="must be a string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": 456})


def test_from_dict_rejects_list_timestamp() -> None:
    """from_dict should reject list values for updated_at."""
    with pytest.raises(ValueError, match="must be a string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": ["not", "a", "string"]})


def test_from_dict_rejects_dict_timestamp() -> None:
    """from_dict should reject dict values for created_at."""
    with pytest.raises(ValueError, match="must be a string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": {"key": "value"}})


def test_from_dict_rejects_bool_timestamp() -> None:
    """from_dict should reject boolean values for timestamps."""
    with pytest.raises(ValueError, match="must be a string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": True})


def test_from_dict_accepts_empty_string_timestamp() -> None:
    """from_dict should accept empty strings for timestamps (backward compatibility)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})
    # Empty string triggers __post_init__ to set current timestamp
    assert todo.created_at != ""  # __post_init__ filled it


def test_from_dict_accepts_iso_string_timestamp() -> None:
    """from_dict should accept valid ISO format strings."""
    iso_time = "2024-01-01T00:00:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": iso_time})
    assert todo.created_at == iso_time


def test_from_dict_accepts_iso_string_updated_at() -> None:
    """from_dict should accept valid ISO format strings for updated_at."""
    iso_time = "2024-12-31T23:59:59+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": iso_time})
    assert todo.updated_at == iso_time


def test_from_dict_defaults_timestamps_when_missing() -> None:
    """from_dict should work without timestamp fields (defaults apply via __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # Timestamps should be populated by __post_init__
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_from_dict_rejects_none_timestamp_explicit() -> None:
    """from_dict should reject None values for timestamps when explicitly passed."""
    with pytest.raises(ValueError, match="must be a string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": None})
