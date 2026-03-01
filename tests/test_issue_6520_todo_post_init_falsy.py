"""Tests for Todo.__post_init__ handling of empty string falsy values (Issue #6520).

These tests verify that:
1. When user explicitly passes created_at='', it should be auto-filled with current time
2. When user explicitly passes a valid ISO timestamp, it should NOT be overwritten
3. When user omits created_at (default ''), it should be auto-filled with current time
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_created_at_with_valid_iso_string_not_overwritten() -> None:
    """When user provides a valid ISO timestamp, it should NOT be overwritten."""
    explicit_time = "2024-01-01T00:00:00+00:00"
    todo = Todo(id=1, text="test", created_at=explicit_time)

    # The explicitly provided timestamp should be preserved
    assert todo.created_at == explicit_time


def test_todo_created_at_with_empty_string_auto_filled() -> None:
    """When user explicitly passes created_at='', it should be auto-filled with current time."""
    todo = Todo(id=1, text="test", created_at="")

    # Empty string should trigger auto-fill (same as default behavior)
    assert todo.created_at != ""
    assert todo.created_at != ""  # Should have a real timestamp now


def test_todo_created_at_default_auto_filled() -> None:
    """When user omits created_at, it should be auto-filled with current time."""
    todo = Todo(id=1, text="test")

    # Default empty string should trigger auto-fill
    assert todo.created_at != ""


def test_todo_updated_at_with_empty_string_uses_created_at() -> None:
    """When updated_at is empty string, it should use created_at value."""
    explicit_time = "2024-01-01T12:00:00+00:00"
    todo = Todo(id=1, text="test", created_at=explicit_time, updated_at="")

    # Empty updated_at should use created_at value
    assert todo.updated_at == explicit_time


def test_todo_both_timestamps_empty_auto_filled() -> None:
    """When both timestamps are empty strings, both should be auto-filled."""
    todo = Todo(id=1, text="test", created_at="", updated_at="")

    # Both should be auto-filled
    assert todo.created_at != ""
    assert todo.updated_at != ""
    # updated_at should equal created_at when not provided
    assert todo.updated_at == todo.created_at
