"""Tests for timestamp invariant validation (Issue #7329).

These tests verify that:
1. Todo.from_dict validates that created_at <= updated_at
2. The invariant is properly enforced when loading data
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_updated_at_before_created_at() -> None:
    """Todo.from_dict should reject data where updated_at is before created_at."""
    # created_at is 2024-01-02, but updated_at is 2024-01-01 (earlier)
    with pytest.raises(
        ValueError, match=r"updated_at.*before.*created_at|timestamp.*invalid|invariant"
    ):
        Todo.from_dict(
            {
                "id": 1,
                "text": "task",
                "created_at": "2024-01-02T00:00:00+00:00",
                "updated_at": "2024-01-01T00:00:00+00:00",
            }
        )


def test_todo_from_dict_accepts_updated_at_equal_to_created_at() -> None:
    """Todo.from_dict should accept data where updated_at equals created_at."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
        }
    )
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
    assert todo.updated_at == "2024-01-01T00:00:00+00:00"


def test_todo_from_dict_accepts_updated_at_after_created_at() -> None:
    """Todo.from_dict should accept data where updated_at is after created_at."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T00:00:00+00:00",
        }
    )
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
    assert todo.updated_at == "2024-01-02T00:00:00+00:00"


def test_todo_from_dict_accepts_empty_timestamps() -> None:
    """Todo.from_dict should accept empty/missing timestamps (defaults will be set)."""
    # Missing timestamps - __post_init__ will set them
    todo1 = Todo.from_dict({"id": 1, "text": "task"})
    assert todo1.created_at != ""
    assert todo1.updated_at != ""

    # Empty string timestamps - __post_init__ will set them
    todo2 = Todo.from_dict({"id": 2, "text": "task", "created_at": "", "updated_at": ""})
    assert todo2.created_at != ""
    assert todo2.updated_at != ""
