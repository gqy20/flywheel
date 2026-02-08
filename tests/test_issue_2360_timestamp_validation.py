"""Tests for timestamp format validation in Todo.from_dict() (Issue #2360).

These tests verify that:
1. Invalid timestamp strings are rejected or handled gracefully
2. Empty timestamps trigger __post_init__ default behavior
3. Valid ISO8601 timestamps are preserved
4. Roundtrip serialization preserves valid timestamps
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_rejects_invalid_timestamp_string() -> None:
    """Todo.from_dict should replace invalid timestamp string with current UTC time."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "invalid-timestamp",
        "updated_at": "also-invalid"
    })

    # Should have valid ISO8601 timestamps now
    assert todo.created_at != "invalid-timestamp"
    assert todo.updated_at != "also-invalid"
    # Should be valid ISO8601 format (contains 'T' and ends with Z or +HH:MM)
    assert "T" in todo.created_at or "+" in todo.created_at


def test_from_dict_handles_empty_timestamp_gracefully() -> None:
    """Todo.from_dict should handle empty string by letting __post_init__ set defaults."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "",
        "updated_at": ""
    })

    # Empty strings should trigger __post_init__ to set current time
    assert todo.created_at != ""
    assert todo.updated_at != ""
    assert "T" in todo.created_at or "+" in todo.created_at


def test_from_dict_handles_missing_timestamp_field() -> None:
    """Todo.from_dict should handle missing timestamp fields gracefully."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task"
    })

    # Missing fields should trigger __post_init__ defaults
    assert todo.created_at != ""
    assert todo.updated_at != ""
    assert "T" in todo.created_at or "+" in todo.created_at


def test_from_dict_handles_integer_timestamp() -> None:
    """Todo.from_dict should handle integer timestamp by converting to valid ISO8601."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": 1234567890,
        "updated_at": 9876543210
    })

    # Should not be the string "1234567890"
    assert todo.created_at not in ("1234567890", "")
    # Should be valid ISO8601 format
    assert "T" in todo.created_at or "+" in todo.created_at


def test_from_dict_handles_none_timestamp() -> None:
    """Todo.from_dict should handle None value for timestamp fields."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": None,
        "updated_at": None
    })

    # Should not be "None" string
    assert todo.created_at not in ("None", "")
    assert todo.updated_at not in ("None", "")


def test_from_dict_preserves_valid_iso8601_timestamp() -> None:
    """Todo.from_dict should preserve valid ISO8601 timestamps."""
    valid_timestamp = "2025-01-15T10:30:45+00:00"
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": valid_timestamp,
        "updated_at": valid_timestamp
    })

    assert todo.created_at == valid_timestamp
    assert todo.updated_at == valid_timestamp


def test_from_dict_preserves_iso8601_with_z_suffix() -> None:
    """Todo.from_dict should preserve ISO8601 timestamps with Z suffix."""
    valid_timestamp = "2025-01-15T10:30:45Z"
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": valid_timestamp,
        "updated_at": valid_timestamp
    })

    assert todo.created_at == valid_timestamp
    assert todo.updated_at == valid_timestamp


def test_roundtrip_to_dict_from_dict_preserves_timestamps() -> None:
    """Roundtrip Todo -> to_dict() -> from_dict() should preserve valid timestamps."""
    original = Todo(id=1, text="task", done=False)
    original.created_at = "2025-01-15T10:30:45+00:00"
    original.updated_at = "2025-01-15T11:30:45+00:00"

    # Serialize and deserialize
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done


def test_from_dict_rejects_numeric_string_timestamp() -> None:
    """Todo.from_dict should reject numeric strings as invalid timestamps."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "1234567890",
        "updated_at": "9876543210"
    })

    # Should replace with valid timestamp, not keep the numeric string
    assert todo.created_at != "1234567890"
    assert todo.updated_at != "9876543210"
    assert "T" in todo.created_at or "+" in todo.created_at
