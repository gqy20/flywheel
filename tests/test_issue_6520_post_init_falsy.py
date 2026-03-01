"""Tests for Todo.__post_init__ handling of empty string falsy values (Issue #6520).

These tests verify that:
1. Todo with explicit valid ISO timestamp should NOT be overwritten
2. Todo with explicit empty string created_at should be auto-filled (same as default)
3. Todo with no created_at provided should be auto-filled
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_created_at_with_valid_timestamp_not_overwritten() -> None:
    """When user explicitly provides a valid ISO timestamp, it should NOT be overwritten."""
    explicit_timestamp = "2024-01-01T00:00:00+00:00"
    todo = Todo(id=1, text="test", created_at=explicit_timestamp)

    # The explicitly provided timestamp should be preserved
    assert todo.created_at == explicit_timestamp


def test_todo_created_at_with_empty_string_is_auto_filled() -> None:
    """When user explicitly passes created_at='', it should be auto-filled with current time."""
    todo = Todo(id=1, text="test", created_at="")

    # Empty string should trigger auto-fill (same behavior as default)
    assert todo.created_at != ""
    assert "T" in todo.created_at  # Basic ISO format check


def test_todo_created_at_default_is_auto_filled() -> None:
    """When created_at is not provided (uses default), it should be auto-filled."""
    todo = Todo(id=1, text="test")

    # Default empty string should be auto-filled
    assert todo.created_at != ""
    assert "T" in todo.created_at  # Basic ISO format check


def test_todo_updated_at_with_empty_string_uses_created_at() -> None:
    """When updated_at is empty string, it should use the auto-filled created_at."""
    todo = Todo(id=1, text="test", created_at="", updated_at="")

    # Both should be auto-filled and updated_at should equal created_at
    assert todo.created_at != ""
    assert todo.updated_at == todo.created_at


def test_todo_updated_at_with_valid_created_at_preserved() -> None:
    """When valid created_at is provided but updated_at is empty, updated_at uses created_at."""
    explicit_timestamp = "2024-01-01T00:00:00+00:00"
    todo = Todo(id=1, text="test", created_at=explicit_timestamp, updated_at="")

    # created_at should be preserved, updated_at should equal created_at
    assert todo.created_at == explicit_timestamp
    assert todo.updated_at == explicit_timestamp
