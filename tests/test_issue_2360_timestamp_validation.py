"""Tests for timestamp validation in Todo.from_dict() (Issue #2360).

These tests verify that:
1. Invalid timestamp strings are replaced with current UTC timestamp
2. Valid ISO8601 timestamps are preserved
3. Roundtrip (Todo -> to_dict -> from_dict) preserves valid timestamps
"""

from __future__ import annotations

import re

from flywheel.todo import Todo


def test_todo_from_dict_replaces_invalid_timestamp_string() -> None:
    """Todo.from_dict should replace invalid timestamp strings with current UTC timestamp."""
    # Data with invalid timestamp string
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": "invalid-string"})

    # Should have a valid ISO8601 timestamp (not the invalid string)
    assert todo.created_at != "invalid-string"
    # ISO8601 timestamps contain 'T' and match pattern like: 2026-02-08T12:00:00
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.created_at)


def test_todo_from_dict_replaces_none_timestamp() -> None:
    """Todo.from_dict should replace None timestamp values with current UTC timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})

    # Should have a valid ISO8601 timestamp (not "None")
    assert todo.created_at != "None"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.created_at)


def test_todo_from_dict_converts_integer_timestamp() -> None:
    """Todo.from_dict should handle integer timestamp values (convert or replace)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": 123})

    # Should have a valid ISO8601 timestamp (not "123")
    assert todo.created_at != "123"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.created_at)


def test_todo_from_dict_handles_empty_string_timestamp() -> None:
    """Todo.from_dict should handle empty string timestamp (triggers __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})

    # Empty string should trigger __post_init__ which sets it to current timestamp
    assert todo.created_at != ""
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.created_at)


def test_todo_from_dict_preserves_valid_iso8601_timestamp() -> None:
    """Todo.from_dict should preserve valid ISO8601 timestamps."""
    valid_timestamp = "2026-02-08T12:00:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": valid_timestamp})

    # Should preserve the valid timestamp
    assert todo.created_at == valid_timestamp


def test_todo_from_dict_preserves_valid_iso8601_timestamp_basic_format() -> None:
    """Todo.from_dict should preserve valid ISO8601 timestamps in basic format."""
    valid_timestamp = "2026-02-08T12:00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": valid_timestamp})

    # Should preserve the valid timestamp
    assert todo.created_at == valid_timestamp


def test_todo_from_dict_handles_both_timestamps_invalid() -> None:
    """Todo.from_dict should handle both created_at and updated_at being invalid."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "bogus-created",
        "updated_at": "bogus-updated"
    })

    # Both should be replaced with valid timestamps
    assert todo.created_at != "bogus-created"
    assert todo.updated_at != "bogus-updated"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.created_at)
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.updated_at)


def test_todo_roundtrip_preserves_valid_timestamps() -> None:
    """Todo -> to_dict() -> from_dict() should preserve valid ISO8601 timestamps."""
    original = Todo(id=1, text="task")
    # Get the auto-generated timestamp
    original_created = original.created_at
    original_updated = original.updated_at

    # Convert to dict and back
    data = original.to_dict()
    restored = Todo.from_dict(data)

    # Timestamps should be preserved
    assert restored.created_at == original_created
    assert restored.updated_at == original_updated


def test_todo_from_dict_handles_various_invalid_formats() -> None:
    """Todo.from_dict should reject various invalid timestamp formats."""
    invalid_timestamps = [
        "None",
        "0",
        "yesterday",
        "2024/13/01",  # Invalid month
        "2024-02-30",   # Invalid day
        "abc123",
        "---",
    ]

    for invalid_ts in invalid_timestamps:
        todo = Todo.from_dict({"id": 1, "text": "task", "created_at": invalid_ts})
        # Should have a valid ISO8601 timestamp (not the invalid string)
        assert todo.created_at != invalid_ts
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.created_at)
