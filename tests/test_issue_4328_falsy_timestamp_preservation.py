"""Tests for preserving falsy created_at/updated_at values (Issue #4328).

These tests verify that:
1. Todo.from_dict preserves explicit created_at string exactly
2. Todo.from_dict generates timestamp when created_at is missing
3. Todo.from_dict with created_at=None treats it as 'not provided' (generates new timestamp)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_preserves_explicit_created_at_string() -> None:
    """Todo.from_dict should preserve explicit created_at string exactly."""
    explicit_timestamp = "2023-01-01T00:00:00"
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": explicit_timestamp})
    assert todo.created_at == explicit_timestamp


def test_from_dict_preserves_explicit_updated_at_string() -> None:
    """Todo.from_dict should preserve explicit updated_at string exactly."""
    explicit_timestamp = "2023-01-01T12:30:00"
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": explicit_timestamp})
    assert todo.updated_at == explicit_timestamp


def test_from_dict_generates_timestamp_when_created_at_missing() -> None:
    """Todo.from_dict should generate timestamp when created_at is missing."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    # Should have a non-empty timestamp
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format contains 'T'


def test_from_dict_generates_timestamp_when_created_at_is_none() -> None:
    """Todo.from_dict should treat None as 'not provided' and generate timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})
    # None should be treated as "not provided", generating a new timestamp
    assert todo.created_at != ""
    assert "T" in todo.created_at


def test_from_dict_generates_timestamp_when_updated_at_is_none() -> None:
    """Todo.from_dict should treat None as 'not provided' and generate timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": None})
    # None should be treated as "not provided", generating a new timestamp
    assert todo.updated_at != ""
    assert "T" in todo.updated_at


def test_from_dict_preserves_both_timestamps() -> None:
    """Todo.from_dict should preserve both timestamps when both are provided."""
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


def test_from_dict_preserves_zero_as_valid_timestamp() -> None:
    """Todo.from_dict should treat 0 as a valid timestamp string, not falsy."""
    # While "0" is an unusual timestamp, it should be preserved as-is
    # rather than being converted to a new timestamp
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": 0})
    assert todo.created_at == "0"


def test_from_dict_preserves_false_as_valid_timestamp() -> None:
    """Todo.from_dict should convert False to "False", not treat it as missing."""
    # While "False" is an unusual timestamp, it should be preserved as the string
    # rather than being converted to a new timestamp
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": False})
    assert todo.created_at == "False"
