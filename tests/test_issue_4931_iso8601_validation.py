"""Tests for issue #4931: ISO 8601 timestamp validation in from_dict."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_invalid_iso8601_created_at() -> None:
    """Bug #4931: from_dict should reject invalid ISO 8601 created_at timestamps."""
    with pytest.raises(ValueError, match=r"created_at.*ISO 8601"):
        Todo.from_dict({
            "id": 1,
            "text": "test",
            "created_at": "not-a-date",
        })


def test_from_dict_rejects_malformed_iso8601_created_at() -> None:
    """Bug #4931: from_dict should reject malformed ISO 8601 created_at timestamps."""
    with pytest.raises(ValueError, match=r"created_at.*ISO 8601"):
        Todo.from_dict({
            "id": 1,
            "text": "test",
            "created_at": "2024-13-45T99:99:99",  # Invalid month/day/time
        })


def test_from_dict_rejects_invalid_iso8601_updated_at() -> None:
    """Bug #4931: from_dict should reject invalid ISO 8601 updated_at timestamps."""
    with pytest.raises(ValueError, match=r"updated_at.*ISO 8601"):
        Todo.from_dict({
            "id": 1,
            "text": "test",
            "updated_at": "invalid-date",
        })


def test_from_dict_rejects_malformed_iso8601_updated_at() -> None:
    """Bug #4931: from_dict should reject malformed ISO 8601 updated_at timestamps."""
    with pytest.raises(ValueError, match=r"updated_at.*ISO 8601"):
        Todo.from_dict({
            "id": 1,
            "text": "test",
            "updated_at": "2024-02-30T25:00:00",  # Invalid day/hour
        })


def test_from_dict_accepts_valid_iso8601_created_at() -> None:
    """Bug #4931: from_dict should still accept valid ISO 8601 created_at timestamps."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "2024-01-15T10:30:00+00:00",
    })
    assert todo.created_at == "2024-01-15T10:30:00+00:00"


def test_from_dict_accepts_valid_iso8601_updated_at() -> None:
    """Bug #4931: from_dict should still accept valid ISO 8601 updated_at timestamps."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "updated_at": "2024-01-15T10:30:00Z",
    })
    assert todo.updated_at == "2024-01-15T10:30:00Z"


def test_from_dict_accepts_valid_iso8601_utc_format() -> None:
    """Bug #4931: from_dict should accept ISO 8601 format from datetime.isoformat()."""
    # This is the format produced by _utc_now_iso()
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "2024-01-15T10:30:00.123456+00:00",
        "updated_at": "2024-01-15T10:35:00.123456+00:00",
    })
    assert todo.created_at == "2024-01-15T10:30:00.123456+00:00"
    assert todo.updated_at == "2024-01-15T10:35:00.123456+00:00"


def test_from_dict_accepts_empty_timestamps() -> None:
    """Bug #4931: Empty timestamps should still be accepted (will be auto-filled)."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "",
        "updated_at": "",
    })
    # Empty strings trigger __post_init__ to fill them
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_from_dict_accepts_missing_timestamps() -> None:
    """Bug #4931: Missing timestamps should still be accepted (will be auto-filled)."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
    })
    # Missing fields trigger __post_init__ to fill them
    assert todo.created_at != ""
    assert todo.updated_at != ""
