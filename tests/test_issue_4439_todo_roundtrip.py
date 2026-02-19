"""Tests for Todo to_dict/from_dict round-trip invariance.

Issue: #4439 - No tests for to_dict/from_dict round-trip invariance
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_roundtrip_basic() -> None:
    """Verify Todo.from_dict(todo.to_dict()) produces equivalent object."""
    original = Todo(id=1, text="test todo")
    reconstructed = Todo.from_dict(original.to_dict())

    assert reconstructed.id == original.id
    assert reconstructed.text == original.text
    assert reconstructed.done == original.done
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at


def test_todo_roundtrip_with_done_true() -> None:
    """Verify round-trip works when done=True."""
    original = Todo(id=42, text="completed task", done=True)
    reconstructed = Todo.from_dict(original.to_dict())

    assert reconstructed.id == original.id
    assert reconstructed.text == original.text
    assert reconstructed.done is True
    assert reconstructed.done == original.done
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at


def test_todo_roundtrip_with_non_empty_timestamps() -> None:
    """Verify round-trip works with explicit non-empty timestamps."""
    original = Todo(
        id=99,
        text="task with timestamps",
        done=True,
        created_at="2024-01-15T10:30:00+00:00",
        updated_at="2024-01-16T14:45:00+00:00",
    )
    reconstructed = Todo.from_dict(original.to_dict())

    assert reconstructed.id == original.id
    assert reconstructed.text == original.text
    assert reconstructed.done == original.done
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at


def test_todo_roundtrip_preserves_all_fields() -> None:
    """Verify all fields are preserved in round-trip, including edge cases."""
    original = Todo(id=0, text="", done=False)
    reconstructed = Todo.from_dict(original.to_dict())

    assert reconstructed.id == original.id
    assert reconstructed.text == original.text
    assert reconstructed.done == original.done
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at
