"""Tests for timestamp format validation in Todo.from_dict() (Issue #2360).

These tests verify that:
1. Invalid timestamp strings are rejected or replaced with valid timestamps
2. Type coercion for timestamps works correctly (integers, None, etc.)
3. Empty strings still trigger __post_init__ for timestamp generation
4. Valid ISO8601 timestamps are preserved during roundtrip
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_todo_from_dict_rejects_invalid_timestamp_string() -> None:
    """Todo.from_dict should replace invalid timestamp strings with valid ISO8601 timestamps."""
    # Create a todo with invalid timestamp string
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": "invalid-string"})

    # The invalid string should be replaced (either with empty string triggering __post_init__ or directly with valid timestamp)
    # Verify it's a valid ISO8601 timestamp now
    assert todo.created_at != "invalid-string"
    # Should be parseable as ISO8601 or be a valid timestamp format
    try:
        datetime.fromisoformat(todo.created_at.replace("Z", "+00:00"))
    except ValueError:
        # If it has 'Z' suffix, try parsing with datetime.strptime
        pytest.fail(f"created_at '{todo.created_at}' is not a valid ISO8601 timestamp")


def test_todo_from_dict_handles_none_timestamp() -> None:
    """Todo.from_dict should handle None values for timestamp fields."""
    # When created_at is None in JSON, str(None) becomes "None"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})

    # The "None" string should be replaced with a valid timestamp
    assert todo.created_at != "None"
    assert todo.created_at  # Should not be empty


def test_todo_from_dict_handles_integer_timestamp() -> None:
    """Todo.from_dict should handle integer values for timestamp fields."""
    # Unix timestamp or other integer should be converted to valid ISO8601 or replaced
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": 1234567890})

    # Integer timestamp should be converted to valid ISO8601 or replaced
    assert todo.created_at != "1234567890"
    assert todo.created_at  # Should not be empty


def test_todo_from_dict_preserves_empty_string() -> None:
    """Todo.from_dict should preserve empty string which triggers __post_init__."""
    # Empty string should trigger __post_init__ to set timestamp
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})

    # Empty string triggers __post_init__, so created_at should be set
    assert todo.created_at
    assert todo.created_at != ""


def test_todo_from_dict_preserves_valid_iso8601_timestamp() -> None:
    """Todo.from_dict should preserve valid ISO8601 timestamps during roundtrip."""
    # Create a valid ISO8601 timestamp
    valid_timestamp = datetime.now(UTC).isoformat()

    # Create todo from dict with valid timestamp
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": valid_timestamp})

    # The valid timestamp should be preserved
    assert todo.created_at == valid_timestamp


def test_todo_roundtrip_preserves_valid_timestamps() -> None:
    """Todo -> to_dict() -> from_dict() should preserve valid timestamps."""
    # Create original todo with timestamps
    original = Todo(id=1, text="task")
    original_created = original.created_at

    # Convert to dict and back
    todo_dict = original.to_dict()
    restored = Todo.from_dict(todo_dict)

    # Timestamps should be preserved
    assert restored.created_at == original_created


def test_storage_load_replaces_invalid_timestamps(tmp_path) -> None:
    """Storage.load() should replace invalid timestamps when loading from JSON."""
    db = tmp_path / "invalid_timestamps.json"
    storage = TodoStorage(str(db))

    # Write JSON with invalid timestamp
    db.write_text(
        '[{"id": 1, "text": "task", "created_at": "invalid-timestamp", "done": false}]',
        encoding="utf-8",
    )

    # Loading should not fail and should replace invalid timestamp
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "task"
    assert loaded[0].created_at != "invalid-timestamp"
    assert loaded[0].created_at  # Should be a valid timestamp now
