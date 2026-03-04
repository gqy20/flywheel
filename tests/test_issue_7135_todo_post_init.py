"""Tests for Todo.__post_init__ method (Issue #7135).

These tests verify that:
1. created_at is auto-generated as ISO format when not provided
2. updated_at equals created_at when not provided
3. Explicit created_at/updated_at are not overwritten
"""

from __future__ import annotations

import re

from flywheel.todo import Todo

# ISO 8601 format regex pattern (basic validation)
ISO_8601_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$"
)


def test_todo_post_init_auto_generates_created_at() -> None:
    """created_at should be auto-generated when not provided."""
    todo = Todo(id=1, text="test task")

    # created_at should be non-empty
    assert todo.created_at, "created_at should be auto-generated"

    # created_at should match ISO 8601 format
    assert ISO_8601_PATTERN.match(
        todo.created_at
    ), f"created_at should be ISO format, got: {todo.created_at}"


def test_todo_post_init_updated_at_equals_created_at() -> None:
    """updated_at should equal created_at when not provided."""
    todo = Todo(id=1, text="test task")

    # updated_at should equal created_at when not explicitly set
    assert (
        todo.updated_at == todo.created_at
    ), f"updated_at ({todo.updated_at}) should equal created_at ({todo.created_at})"


def test_todo_post_init_preserves_explicit_created_at() -> None:
    """Explicit created_at should not be overwritten."""
    explicit_time = "2024-01-01T12:00:00+00:00"
    todo = Todo(id=1, text="test task", created_at=explicit_time)

    assert (
        todo.created_at == explicit_time
    ), f"created_at should be preserved, expected {explicit_time}, got {todo.created_at}"


def test_todo_post_init_preserves_explicit_updated_at() -> None:
    """Explicit updated_at should not be overwritten."""
    explicit_time = "2024-01-01T12:00:00+00:00"
    todo = Todo(id=1, text="test task", updated_at=explicit_time)

    assert (
        todo.updated_at == explicit_time
    ), f"updated_at should be preserved, expected {explicit_time}, got {todo.updated_at}"


def test_todo_post_init_both_timestamps_explicit() -> None:
    """Both explicit timestamps should be preserved."""
    created = "2024-01-01T10:00:00+00:00"
    updated = "2024-01-02T15:30:00+00:00"
    todo = Todo(id=1, text="test task", created_at=created, updated_at=updated)

    assert todo.created_at == created
    assert todo.updated_at == updated


def test_todo_post_init_created_at_only_explicit() -> None:
    """When only created_at is explicit, updated_at should equal it."""
    explicit_created = "2024-01-01T10:00:00+00:00"
    todo = Todo(id=1, text="test task", created_at=explicit_created)

    assert (
        todo.created_at == explicit_created
    ), "created_at should be preserved when explicitly set"
    assert (
        todo.updated_at == explicit_created
    ), "updated_at should equal created_at when not explicitly set"
