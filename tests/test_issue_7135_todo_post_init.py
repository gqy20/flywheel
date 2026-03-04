"""Tests for Todo.__post_init__ method (Issue #7135).

These tests verify that:
1. created_at is auto-generated as ISO format when not provided
2. updated_at equals created_at when not provided
3. Explicit created_at/updated_at values are not overwritten
"""

from __future__ import annotations

import re

from flywheel.todo import Todo

# ISO 8601 format regex pattern (basic validation)
ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def test_todo_post_init_auto_generates_created_at() -> None:
    """__post_init__ should auto-generate created_at as ISO format when not provided."""
    todo = Todo(id=1, text="test task")

    # created_at should be non-empty and in ISO format
    assert todo.created_at, "created_at should be auto-generated"
    assert ISO_PATTERN.match(todo.created_at), (
        f"created_at should be ISO format, got: {todo.created_at}"
    )


def test_todo_post_init_updated_at_defaults_to_created_at() -> None:
    """__post_init__ should set updated_at equal to created_at when not provided."""
    todo = Todo(id=1, text="test task")

    # updated_at should equal created_at when not explicitly set
    assert todo.updated_at == todo.created_at, (
        f"updated_at should equal created_at, got: {todo.updated_at} vs {todo.created_at}"
    )


def test_todo_post_init_preserves_explicit_created_at() -> None:
    """__post_init__ should not overwrite explicitly provided created_at."""
    explicit_time = "2024-01-01T12:00:00+00:00"
    todo = Todo(id=1, text="test task", created_at=explicit_time)

    # created_at should remain unchanged
    assert todo.created_at == explicit_time, (
        f"created_at should be preserved, got: {todo.created_at}"
    )


def test_todo_post_init_preserves_explicit_updated_at() -> None:
    """__post_init__ should not overwrite explicitly provided updated_at."""
    explicit_time = "2024-01-01T12:00:00+00:00"
    todo = Todo(id=1, text="test task", updated_at=explicit_time)

    # updated_at should remain unchanged
    assert todo.updated_at == explicit_time, (
        f"updated_at should be preserved, got: {todo.updated_at}"
    )


def test_todo_post_init_both_timestamps_explicit() -> None:
    """__post_init__ should preserve both timestamps when both are explicit."""
    created = "2024-01-01T10:00:00+00:00"
    updated = "2024-01-02T15:30:00+00:00"
    todo = Todo(id=1, text="test task", created_at=created, updated_at=updated)

    # Both timestamps should be preserved exactly
    assert todo.created_at == created, f"created_at should be {created}, got: {todo.created_at}"
    assert todo.updated_at == updated, f"updated_at should be {updated}, got: {todo.updated_at}"
