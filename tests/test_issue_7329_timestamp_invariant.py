"""Tests for issue #7329: created_at <= updated_at invariant validation."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_updated_at_before_created_at() -> None:
    """Issue #7329: from_dict should reject updated_at before created_at."""
    data = {
        "id": 1,
        "text": "test todo",
        "done": False,
        "created_at": "2026-03-05T12:00:00+00:00",
        "updated_at": "2026-03-05T10:00:00+00:00",  # Before created_at
    }

    with pytest.raises(ValueError, match=r"updated_at.*must not be before.*created_at"):
        Todo.from_dict(data)


def test_from_dict_accepts_updated_at_equal_to_created_at() -> None:
    """Issue #7329: from_dict should accept updated_at equal to created_at."""
    data = {
        "id": 1,
        "text": "test todo",
        "done": False,
        "created_at": "2026-03-05T12:00:00+00:00",
        "updated_at": "2026-03-05T12:00:00+00:00",
    }

    todo = Todo.from_dict(data)
    assert todo.created_at == "2026-03-05T12:00:00+00:00"
    assert todo.updated_at == "2026-03-05T12:00:00+00:00"


def test_from_dict_accepts_updated_at_after_created_at() -> None:
    """Issue #7329: from_dict should accept updated_at after created_at."""
    data = {
        "id": 1,
        "text": "test todo",
        "done": False,
        "created_at": "2026-03-05T10:00:00+00:00",
        "updated_at": "2026-03-05T12:00:00+00:00",
    }

    todo = Todo.from_dict(data)
    assert todo.created_at == "2026-03-05T10:00:00+00:00"
    assert todo.updated_at == "2026-03-05T12:00:00+00:00"


def test_from_dict_accepts_empty_timestamps() -> None:
    """Issue #7329: from_dict should accept empty timestamps (defaults applied)."""
    data = {
        "id": 1,
        "text": "test todo",
        "done": False,
    }

    todo = Todo.from_dict(data)
    # __post_init__ sets timestamps, and they should be equal initially
    assert todo.created_at == todo.updated_at


def test_from_dict_rejects_invalid_timestamp_format() -> None:
    """Issue #7329: from_dict should reject invalid timestamp format."""
    data = {
        "id": 1,
        "text": "test todo",
        "done": False,
        "created_at": "not-a-valid-timestamp",
        "updated_at": "2026-03-05T12:00:00+00:00",
    }

    with pytest.raises(ValueError, match="Invalid timestamp format"):
        Todo.from_dict(data)


def test_mark_done_preserves_invariant() -> None:
    """Issue #7329: mark_done should preserve created_at <= updated_at invariant."""
    todo = Todo(id=1, text="test todo")
    created = todo.created_at

    todo.mark_done()

    assert todo.updated_at >= created
