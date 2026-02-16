"""Tests for to_dict/from_dict round-trip preserving all fields (Issue #3734).

These tests verify that:
1. Todo.to_dict() -> Todo.from_dict() round-trip preserves all fields
2. Timestamps (created_at, updated_at) are preserved during round-trip
3. Edge cases with special characters and long text are handled correctly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_to_dict_from_dict_roundtrip_preserves_all_fields() -> None:
    """Todo.to_dict() -> Todo.from_dict() should preserve all fields including timestamps."""
    original = Todo(
        id=42,
        text="Sample task",
        done=True,
        created_at="2024-01-15T10:30:00+00:00",
        updated_at="2024-01-16T14:45:00+00:00",
    )

    dict_repr = original.to_dict()
    restored = Todo.from_dict(dict_repr)

    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_default_values() -> None:
    """Round-trip should work with default done=False and auto-generated timestamps."""
    original = Todo(id=1, text="New task")
    dict_repr = original.to_dict()
    restored = Todo.from_dict(dict_repr)

    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done is False
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_long_text() -> None:
    """Round-trip should preserve long text correctly."""
    long_text = "A" * 1000  # Very long task description
    original = Todo(
        id=99,
        text=long_text,
        done=False,
        created_at="2024-02-01T00:00:00+00:00",
        updated_at="2024-02-01T00:00:00+00:00",
    )

    dict_repr = original.to_dict()
    restored = Todo.from_dict(dict_repr)

    assert restored.text == long_text
    assert len(restored.text) == 1000


def test_todo_to_dict_from_dict_roundtrip_special_characters() -> None:
    """Round-trip should handle special characters including unicode, quotes, and escape sequences."""
    special_text = "Task with special chars: émoji 🚀, quotes \"'`, escapes \n\t\r"
    original = Todo(
        id=100,
        text=special_text,
        done=True,
        created_at="2024-03-15T12:00:00+00:00",
        updated_at="2024-03-15T12:00:00+00:00",
    )

    dict_repr = original.to_dict()
    restored = Todo.from_dict(dict_repr)

    assert restored.text == special_text
    assert "🚀" in restored.text
    assert "\n" in restored.text
    assert "\t" in restored.text


def test_todo_to_dict_from_dict_roundtrip_empty_timestamps() -> None:
    """Round-trip should handle empty timestamps (edge case)."""
    # Create a todo with empty timestamps by bypassing __post_init__
    # Note: __post_init__ auto-fills timestamps, so this tests the from_dict handling
    original = Todo(id=5, text="Task with empty timestamps")
    dict_repr = original.to_dict()

    # Manually clear timestamps to test edge case
    dict_repr["created_at"] = ""
    dict_repr["updated_at"] = ""

    restored = Todo.from_dict(dict_repr)

    # After round-trip with empty timestamps, __post_init__ will generate new ones
    assert restored.id == 5
    assert restored.text == "Task with empty timestamps"
    # New timestamps should be generated
    assert restored.created_at != ""
    assert restored.updated_at != ""
