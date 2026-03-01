"""Tests for Todo.__post_init__ handling of empty string falsy values (Issue #6520).

These tests verify that:
1. When a valid ISO timestamp is provided, it should NOT be overwritten
2. When an empty string is explicitly passed, it should auto-fill with current time
3. When no value is provided (default), it should auto-fill with current time
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_created_at_not_overwritten_when_valid_iso_provided() -> None:
    """When a valid ISO timestamp is provided, it should NOT be overwritten."""
    explicit_timestamp = "2024-01-01T00:00:00+00:00"
    todo = Todo(id=1, text="test", created_at=explicit_timestamp)

    # The explicitly provided timestamp should be preserved
    assert todo.created_at == explicit_timestamp


def test_todo_created_at_auto_fills_when_empty_string_provided() -> None:
    """When an empty string is explicitly passed, it should auto-fill with current time."""
    todo = Todo(id=1, text="test", created_at="")

    # Empty string should trigger auto-fill, so created_at should now be a valid ISO timestamp
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format contains 'T' separator


def test_todo_created_at_auto_fills_when_default() -> None:
    """When no value is provided (default), it should auto-fill with current time."""
    todo = Todo(id=1, text="test")

    # Default empty string should trigger auto-fill
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format contains 'T' separator


def test_todo_updated_at_not_overwritten_when_valid_iso_provided() -> None:
    """When a valid updated_at ISO timestamp is provided, it should NOT be overwritten."""
    explicit_timestamp = "2024-01-01T00:00:00+00:00"
    todo = Todo(id=1, text="test", created_at="2024-01-01T00:00:00+00:00", updated_at=explicit_timestamp)

    # The explicitly provided timestamp should be preserved
    assert todo.updated_at == explicit_timestamp


def test_todo_updated_at_uses_created_at_when_empty_string_provided() -> None:
    """When updated_at is empty string but created_at is set, use created_at."""
    created_timestamp = "2024-01-01T00:00:00+00:00"
    todo = Todo(id=1, text="test", created_at=created_timestamp, updated_at="")

    # Empty updated_at should be set to created_at value
    assert todo.updated_at == created_timestamp


def test_todo_both_timestamps_auto_fill_when_empty_strings() -> None:
    """When both timestamps are empty strings, both should be auto-filled."""
    todo = Todo(id=1, text="test", created_at="", updated_at="")

    # Both should be filled with current time (created_at first, then updated_at = created_at)
    assert todo.created_at != ""
    assert todo.updated_at != ""
    assert "T" in todo.created_at
    assert "T" in todo.updated_at
    assert todo.updated_at == todo.created_at
