"""Tests for timestamp None handling in Todo.from_dict (Issue #2883).

These tests verify that:
1. None values for created_at/updated_at are converted to empty string, not 'None'
2. Falsy but valid values like 0 are preserved as '0' string
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_from_dict_created_at_none_becomes_empty_string() -> None:
    """Todo.from_dict should convert None for created_at to empty string, not 'None'.

    Note: __post_init__ will fill empty timestamps with current UTC time.
    The key fix is that the timestamp is NOT the corrupted string 'None'.
    """
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})

    # Should NOT be the string 'None' (the bug this fixes)
    assert todo.created_at != "None", "created_at should not be the string 'None'"
    # After __post_init__, empty string gets filled with current timestamp
    assert todo.created_at != "", "Empty timestamp should be filled by __post_init__"
    # Should be a valid ISO timestamp format
    assert "T" in todo.created_at or todo.created_at == "", f"Expected ISO timestamp, got {todo.created_at!r}"


def test_todo_from_dict_updated_at_none_becomes_empty_string() -> None:
    """Todo.from_dict should convert None for updated_at to empty string, not 'None'.

    Note: __post_init__ will fill empty timestamps with current UTC time.
    The key fix is that the timestamp is NOT the corrupted string 'None'.
    """
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": None})

    # Should NOT be the string 'None' (the bug this fixes)
    assert todo.updated_at != "None", "updated_at should not be the string 'None'"
    # After __post_init__, empty string gets filled with current timestamp
    assert todo.updated_at != "", "Empty timestamp should be filled by __post_init__"
    # Should be a valid ISO timestamp format
    assert "T" in todo.updated_at or todo.updated_at == "", f"Expected ISO timestamp, got {todo.updated_at!r}"


def test_todo_from_dict_both_timestamps_none() -> None:
    """Todo.from_dict should handle both timestamps being None without creating 'None' strings."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": None,
        "updated_at": None,
    })

    # Should NOT be the string 'None' (the bug this fixes)
    assert todo.created_at != "None", "created_at should not be the string 'None'"
    assert todo.updated_at != "None", "updated_at should not be the string 'None'"


def test_todo_from_dict_timestamp_zero_preserved() -> None:
    """Todo.from_dict should preserve falsy but valid values like 0 as '0' string."""
    # Zero is a valid (falsy) value that should be converted to string '0'
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": 0,
        "updated_at": 0,
    })

    # Zero should become the string '0', not empty string
    assert todo.created_at == "0", f"Expected '0', got {todo.created_at!r}"
    assert todo.updated_at == "0", f"Expected '0', got {todo.updated_at!r}"


def test_todo_from_dict_missing_timestamps() -> None:
    """Todo.from_dict should handle missing timestamp keys gracefully."""
    todo = Todo.from_dict({"id": 1, "text": "task"})

    # Missing keys (.get() returns None) should NOT result in 'None' string
    # After __post_init__, timestamps are filled with current UTC time
    assert todo.created_at != "None", "created_at should not be the string 'None'"
    assert todo.updated_at != "None", "updated_at should not be the string 'None'"
    # Should be filled by __post_init__ since the original value was empty
    assert todo.created_at != "", "created_at should be filled by __post_init__"
    assert todo.updated_at != "", "updated_at should be filled by __post_init__"


def test_todo_from_dict_valid_timestamp_strings() -> None:
    """Todo.from_dict should preserve valid timestamp strings."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-01-02T12:30:45+00:00",
    })

    assert todo.created_at == "2025-01-01T00:00:00+00:00"
    assert todo.updated_at == "2025-01-02T12:30:45+00:00"
