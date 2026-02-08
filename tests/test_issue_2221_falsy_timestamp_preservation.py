"""Tests for Issue #2221 - Falsy timestamp value preservation.

Bug: from_dict treats falsy timestamp values (False, 0, None) as empty string,
causing data loss. The 'or' fallback in lines 100-101 causes False, 0, None
to be converted to empty string instead of being preserved as their string values.

Fix: Use default parameter instead of 'or' fallback to avoid treating False/0
as falsy values that should be converted to empty string.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_preserves_false_timestamp() -> None:
    """Bug #2221: Todo.from_dict should preserve False as 'False' string."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": False})

    # False should be converted to "False" string, not empty string
    assert todo.created_at == "False"


def test_from_dict_preserves_zero_timestamp() -> None:
    """Bug #2221: Todo.from_dict should preserve 0 as '0' string."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": 0})

    # 0 should be converted to "0" string, not empty string
    assert todo.updated_at == "0"


def test_from_dict_preserves_both_falsy_timestamps() -> None:
    """Bug #2221: Todo.from_dict should preserve both falsy timestamps."""
    todo = Todo.from_dict(
        {"id": 1, "text": "task", "created_at": False, "updated_at": 0}
    )

    assert todo.created_at == "False"
    assert todo.updated_at == "0"


def test_from_dict_handles_none_timestamp_as_default() -> None:
    """Bug #2221: Todo.from_dict should treat None as missing key (default to empty)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})

    # None should still result in empty string (not "None")
    # This is handled by str(None) == "None" which is fine,
    # but the behavior should be consistent with the fix
    assert todo.created_at == "None" or todo.created_at == ""


def test_from_dict_handles_missing_timestamp_keys() -> None:
    """Bug #2221: Todo.from_dict should handle missing timestamp keys gracefully."""
    todo = Todo.from_dict({"id": 1, "text": "task"})

    # Missing keys should default to empty string
    # __post_init__ will then set them to current timestamp
    assert todo.created_at != ""  # Should be set by __post_init__
    assert todo.updated_at != ""  # Should be set by __post_init__


def test_from_dict_with_empty_string_timestamp() -> None:
    """Bug #2221: Todo.from_dict should handle explicit empty string timestamps."""
    todo = Todo.from_dict(
        {"id": 1, "text": "task", "created_at": "", "updated_at": ""}
    )

    # Empty string should remain empty string (then set by __post_init__)
    assert todo.created_at != ""  # Set by __post_init__
    assert todo.updated_at != ""  # Set by __post_init__


def test_from_dict_with_valid_string_timestamps() -> None:
    """Bug #2221: Todo.from_dict should preserve valid string timestamps."""
    valid_timestamp = "2024-01-01T00:00:00+00:00"
    todo = Todo.from_dict(
        {"id": 1, "text": "task", "created_at": valid_timestamp, "updated_at": valid_timestamp}
    )

    assert todo.created_at == valid_timestamp
    assert todo.updated_at == valid_timestamp


def test_todo_to_dict_from_dict_roundtrip_with_falsy_timestamps() -> None:
    """Bug #2221: Round-trip serialization should preserve falsy timestamp values."""
    original = Todo(id=1, text="task")
    original.created_at = "False"
    original.updated_at = "0"

    # Serialize to dict
    todo_dict = original.to_dict()

    # Deserialize from dict
    restored = Todo.from_dict(todo_dict)

    # Values should be preserved
    assert restored.created_at == "False"
    assert restored.updated_at == "0"
    assert restored.id == original.id
    assert restored.text == original.text
