"""Tests for timestamp preservation in Todo.from_dict (Issue #4328).

These tests verify that:
1. Explicit created_at/updated_at strings are preserved exactly
2. Missing keys generate new timestamps (correct behavior)
3. Explicit None is treated as "not provided" and generates new timestamp
4. Empty string triggers new timestamp generation (delegated to __post_init__)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_preserves_explicit_created_at_string() -> None:
    """Todo.from_dict should preserve explicit created_at string exactly."""
    explicit_timestamp = "2023-01-01T00:00:00"
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": explicit_timestamp,
    })
    assert todo.created_at == explicit_timestamp


def test_from_dict_preserves_explicit_updated_at_string() -> None:
    """Todo.from_dict should preserve explicit updated_at string exactly."""
    explicit_timestamp = "2023-02-15T12:30:45"
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "updated_at": explicit_timestamp,
    })
    assert todo.updated_at == explicit_timestamp


def test_from_dict_generates_timestamp_when_created_at_missing() -> None:
    """Todo.from_dict should generate new timestamp when created_at key is missing."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
    })
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format


def test_from_dict_with_none_created_at_treated_as_not_provided() -> None:
    """Todo.from_dict with created_at=None should generate new timestamp.

    Explicit None is treated as "not provided" rather than preserving None.
    This documents current expected behavior.
    """
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": None,
    })
    # None should trigger new timestamp generation, not be preserved as "None"
    assert todo.created_at != ""
    assert todo.created_at != "None"
    assert "T" in todo.created_at  # ISO format


def test_from_dict_preserves_both_timestamps() -> None:
    """Todo.from_dict should preserve both created_at and updated_at."""
    created = "2023-01-01T00:00:00"
    updated = "2023-12-31T23:59:59"
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": created,
        "updated_at": updated,
    })
    assert todo.created_at == created
    assert todo.updated_at == updated


def test_from_dict_empty_string_triggers_new_timestamp() -> None:
    """Empty string for created_at should trigger new timestamp generation.

    This verifies that __post_init__ handles empty string by generating
    a new timestamp.
    """
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "",
    })
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format


def test_from_dict_updated_at_missing_uses_created_at() -> None:
    """When updated_at is missing, it should default to created_at."""
    explicit_created = "2023-06-15T10:00:00"
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": explicit_created,
    })
    assert todo.created_at == explicit_created
    assert todo.updated_at == explicit_created
