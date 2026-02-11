"""Tests for Todo.from_dict handling of None values in created_at/updated_at (Issue #2856).

These tests verify that:
1. Todo.from_dict with explicit None for timestamps should NOT result in 'None' strings
2. Todo.from_dict with missing timestamp keys should work correctly
3. Todo.from_dict with valid timestamp strings preserves them correctly

The potential bug: If code were written as `str(data.get('created_at')) or ''`,
then None would become 'None' string (truthy) instead of empty string.

The fix ensures timestamps are never the literal string 'None'.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_from_dict_with_explicit_none_timestamps() -> None:
    """Todo.from_dict with explicit None for timestamps should NOT produce 'None' strings.

    After __post_init__, empty timestamps are set to actual ISO timestamps.
    The key assertion is that timestamps are NOT the literal string 'None'.
    """
    data = {
        "id": 1,
        "text": "test",
        "created_at": None,
        "updated_at": None,
    }

    todo = Todo.from_dict(data)

    # Should NOT be the literal string 'None' (the bug being prevented)
    assert todo.created_at != "None", "created_at should not be literal 'None' string"
    assert todo.updated_at != "None", "updated_at should not be literal 'None' string"

    # After __post_init__, timestamps should be set to valid ISO timestamps
    assert todo.created_at, "created_at should be set by __post_init__"
    assert todo.updated_at, "updated_at should be set by __post_init__"

    # Should be valid ISO format timestamps (start with year)
    assert todo.created_at[0].isdigit() or todo.created_at[0] == "2", "Should be ISO timestamp"


def test_todo_from_dict_with_missing_timestamp_keys() -> None:
    """Todo.from_dict with missing timestamp keys should work correctly."""
    data = {
        "id": 1,
        "text": "test",
        # created_at and updated_at keys are missing
    }

    todo = Todo.from_dict(data)

    # Should NOT be 'None' strings
    assert todo.created_at != "None", "created_at should not be literal 'None' string"
    assert todo.updated_at != "None", "updated_at should not be literal 'None' string"

    # Should be set by __post_init__ to timestamps
    assert todo.created_at, "created_at should be set by __post_init__"
    assert todo.updated_at, "updated_at should be set by __post_init__"


def test_todo_from_dict_with_valid_timestamps() -> None:
    """Todo.from_dict with valid timestamp strings should preserve them."""
    data = {
        "id": 1,
        "text": "test",
        "created_at": "2024-01-15T10:30:00+00:00",
        "updated_at": "2024-01-16T11:45:00+00:00",
    }

    todo = Todo.from_dict(data)

    # Should preserve the valid timestamps
    assert todo.created_at == "2024-01-15T10:30:00+00:00"
    assert todo.updated_at == "2024-01-16T11:45:00+00:00"


def test_todo_from_dict_with_empty_string_timestamps() -> None:
    """Todo.from_dict with empty string timestamps should trigger __post_init__ to set them."""
    data = {
        "id": 1,
        "text": "test",
        "created_at": "",
        "updated_at": "",
    }

    todo = Todo.from_dict(data)

    # Empty strings should trigger __post_init__ to set timestamps
    # NOT remain as empty strings (this is expected behavior)
    assert todo.created_at != "None", "created_at should not be literal 'None' string"
    assert todo.updated_at != "None", "updated_at should not be literal 'None' string"

    # Should be set to actual timestamps
    assert todo.created_at, "created_at should be set by __post_init__"
    assert todo.updated_at, "updated_at should be set by __post_init__"


def test_todo_from_dict_with_mixed_timestamp_values() -> None:
    """Todo.from_dict with mixed None/empty/valid timestamps should handle each correctly."""
    data = {
        "id": 1,
        "text": "test",
        "created_at": None,
        "updated_at": "2024-01-16T11:45:00+00:00",
    }

    todo = Todo.from_dict(data)

    # created_at should be set by __post_init__ (not 'None' string)
    assert todo.created_at != "None", "created_at should not be literal 'None' string"
    assert todo.created_at, "created_at should be set by __post_init__"

    # updated_at should be preserved exactly
    assert todo.updated_at == "2024-01-16T11:45:00+00:00"
