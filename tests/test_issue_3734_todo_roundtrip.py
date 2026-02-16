"""Tests for Todo.to_dict/from_dict round-trip preserving all fields (Issue #3734).

These tests verify that:
1. Todo.to_dict() -> Todo.from_dict() round-trip preserves all fields
2. Round-trip works for edge cases (long text, special characters)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_to_dict_from_dict_roundtrip_basic() -> None:
    """Basic round-trip should preserve id, text, done, created_at, updated_at."""
    original = Todo(
        id=1,
        text="Buy groceries",
        done=False,
        created_at="2024-01-01T12:00:00+00:00",
        updated_at="2024-01-01T12:00:00+00:00",
    )

    # Perform round-trip
    data = original.to_dict()
    restored = Todo.from_dict(data)

    # Verify all fields match
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_done_true() -> None:
    """Round-trip should preserve done=True state."""
    original = Todo(
        id=42,
        text="Completed task",
        done=True,
        created_at="2024-02-15T08:30:00+00:00",
        updated_at="2024-02-16T14:45:00+00:00",
    )

    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done is True
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_long_text() -> None:
    """Round-trip should handle long text correctly."""
    long_text = "A" * 1000  # 1000 characters
    original = Todo(
        id=100,
        text=long_text,
        done=False,
        created_at="2024-03-01T00:00:00+00:00",
        updated_at="2024-03-01T00:00:00+00:00",
    )

    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.text == long_text
    assert len(restored.text) == 1000
    assert restored.id == original.id
    assert restored.done == original.done


def test_todo_to_dict_from_dict_roundtrip_special_characters() -> None:
    """Round-trip should preserve special characters in text."""
    special_text = "Task with émojis 🎉, ünïcödë, and symbols: <>&\"'\\n\\t"
    original = Todo(
        id=7,
        text=special_text,
        done=True,
        created_at="2024-04-01T10:00:00+00:00",
        updated_at="2024-04-01T11:30:00+00:00",
    )

    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.text == special_text
    assert "émojis 🎉" in restored.text
    assert "ünïcödë" in restored.text
    assert restored.id == original.id
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_with_default_timestamps() -> None:
    """Round-trip should work for Todo created with default timestamps."""
    original = Todo(id=5, text="Auto timestamps")

    data = original.to_dict()
    restored = Todo.from_dict(data)

    # Default timestamps should be preserved
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at
