"""Tests for Todo.__post_init__ method (Issue #7135).

These tests verify that:
1. created_at is auto-generated in ISO format when not provided
2. updated_at equals created_at when not provided
3. Explicitly provided created_at/updated_at values are not overwritten
"""

from __future__ import annotations

import re

from flywheel.todo import Todo


def test_todo_post_init_auto_generates_created_at() -> None:
    """created_at should be auto-generated as ISO format when not provided."""
    todo = Todo(id=1, text="test task")

    # created_at should not be empty
    assert todo.created_at != ""

    # Should be in ISO format (YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM or similar)
    iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    assert re.match(iso_pattern, todo.created_at), (
        f"created_at '{todo.created_at}' is not in ISO format"
    )


def test_todo_post_init_updated_at_defaults_to_created_at() -> None:
    """updated_at should equal created_at when not provided."""
    todo = Todo(id=1, text="test task")

    # When updated_at is not provided, it should equal created_at
    assert todo.updated_at == todo.created_at, (
        f"updated_at '{todo.updated_at}' should equal created_at '{todo.created_at}'"
    )


def test_todo_post_init_preserves_explicit_created_at() -> None:
    """Explicitly provided created_at should not be overwritten."""
    explicit_time = "2024-01-01T12:00:00+00:00"
    todo = Todo(id=1, text="test task", created_at=explicit_time)

    # Explicit created_at should be preserved
    assert todo.created_at == explicit_time, (
        f"created_at '{todo.created_at}' should equal explicit value '{explicit_time}'"
    )


def test_todo_post_init_preserves_explicit_updated_at() -> None:
    """Explicitly provided updated_at should not be overwritten."""
    explicit_created = "2024-01-01T12:00:00+00:00"
    explicit_updated = "2024-01-02T15:30:00+00:00"
    todo = Todo(id=1, text="test task", created_at=explicit_created, updated_at=explicit_updated)

    # Both explicit values should be preserved
    assert todo.created_at == explicit_created, (
        f"created_at '{todo.created_at}' should equal explicit value '{explicit_created}'"
    )
    assert todo.updated_at == explicit_updated, (
        f"updated_at '{todo.updated_at}' should equal explicit value '{explicit_updated}'"
    )


def test_todo_post_init_updated_at_independent_when_provided() -> None:
    """updated_at can be different from created_at when explicitly provided."""
    explicit_created = "2024-01-01T12:00:00+00:00"
    explicit_updated = "2024-06-15T08:45:00+00:00"
    todo = Todo(id=1, text="test task", created_at=explicit_created, updated_at=explicit_updated)

    # updated_at should be different from created_at when explicitly set
    assert todo.updated_at != todo.created_at, (
        "updated_at should differ from created_at when explicitly set to different value"
    )


def test_todo_post_init_created_at_empty_string_triggers_auto_generation() -> None:
    """Empty string for created_at should trigger auto-generation."""
    todo = Todo(id=1, text="test task", created_at="")

    # Empty string should trigger auto-generation
    assert todo.created_at != ""
    iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    assert re.match(iso_pattern, todo.created_at), (
        f"created_at '{todo.created_at}' is not in ISO format"
    )


def test_todo_post_init_updated_at_empty_string_uses_created_at() -> None:
    """Empty string for updated_at should use created_at value."""
    explicit_created = "2024-01-01T12:00:00+00:00"
    todo = Todo(id=1, text="test task", created_at=explicit_created, updated_at="")

    # Empty updated_at should be set to created_at
    assert todo.updated_at == explicit_created, (
        f"updated_at '{todo.updated_at}' should equal created_at '{explicit_created}'"
    )
