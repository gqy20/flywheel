"""Tests for from_dict timestamp preservation (Issue #4548).

These tests verify that:
1. from_dict preserves original timestamps when explicitly provided
2. from_dict handles None timestamps correctly (should not silently regenerate)
3. from_dict handles empty string timestamps correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_preserves_explicit_created_at() -> None:
    """from_dict should preserve the original created_at timestamp when provided."""
    original_timestamp = "2025-01-15T10:30:00+00:00"
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": original_timestamp,
    })
    assert todo.created_at == original_timestamp


def test_from_dict_preserves_explicit_updated_at() -> None:
    """from_dict should preserve the original updated_at timestamp when provided."""
    original_timestamp = "2025-01-15T10:30:00+00:00"
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "updated_at": original_timestamp,
    })
    assert todo.updated_at == original_timestamp


def test_from_dict_with_none_created_at_raises_error() -> None:
    """from_dict with explicit None for created_at should raise a clear error.

    When created_at is explicitly set to None in the input dict, it indicates
    ambiguous intent. The fix rejects None explicitly rather than silently
    converting it to empty string and regenerating the timestamp.
    """
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*None"):
        Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": None,
        })


def test_from_dict_with_none_updated_at_raises_error() -> None:
    """from_dict with explicit None for updated_at should raise a clear error.

    When updated_at is explicitly set to None in the input dict, it indicates
    ambiguous intent. The fix rejects None explicitly rather than silently
    converting it to empty string and regenerating the timestamp.
    """
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*None"):
        Todo.from_dict({
            "id": 1,
            "text": "task",
            "updated_at": None,
        })


def test_from_dict_with_empty_string_timestamps_triggers_regeneration() -> None:
    """from_dict with empty string timestamps should trigger __post_init__ regeneration.

    Empty strings are falsy, so __post_init__ will generate new timestamps.
    This is the expected behavior when deserializing incomplete data.
    """
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "",
        "updated_at": "",
    })
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_from_dict_roundtrip_preserves_timestamps() -> None:
    """to_dict -> from_dict roundtrip should preserve original timestamps."""
    original = Todo(id=1, text="original task")
    original.created_at = "2025-01-15T10:30:00+00:00"
    original.updated_at = "2025-01-16T14:45:00+00:00"

    # Roundtrip through dict
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at
