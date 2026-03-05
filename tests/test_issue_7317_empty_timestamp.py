"""Tests for Todo empty timestamp preservation (Issue #7317).

These tests verify that:
1. Todo.from_dict with empty created_at/updated_at preserves empty string
2. Round-trip Todo -> to_dict -> from_dict preserves timestamps exactly
3. New Todo without timestamps still gets auto-filled timestamps
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_preserves_empty_created_at() -> None:
    """Bug #7317: from_dict with empty created_at should keep empty string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": ""})

    # Empty string should be preserved, not auto-filled
    assert todo.created_at == ""


def test_from_dict_preserves_empty_updated_at() -> None:
    """Bug #7317: from_dict with empty updated_at should keep empty string."""
    todo = Todo.from_dict(
        {"id": 1, "text": "test", "created_at": "2024-01-01T00:00:00+00:00", "updated_at": ""}
    )

    # Empty string should be preserved, not auto-filled
    assert todo.updated_at == ""


def test_roundtrip_preserves_timestamps() -> None:
    """Bug #7317: Round-trip Todo -> to_dict -> from_dict preserves timestamps exactly."""
    original = Todo(id=1, text="a")
    original_created = original.created_at

    # Round-trip through dict
    d = original.to_dict()
    restored = Todo.from_dict(d)

    # Timestamps should be preserved exactly
    assert restored.created_at == original_created
    assert restored.updated_at == original.updated_at


def test_new_todo_still_gets_auto_timestamps() -> None:
    """Verify new Todo without timestamps still gets auto-filled."""
    todo = Todo(id=1, text="new todo")

    # Should have auto-filled timestamps
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_from_dict_with_explicit_timestamps_preserves_them() -> None:
    """from_dict with explicit timestamps should preserve them."""
    explicit_time = "2024-01-01T12:00:00+00:00"
    todo = Todo.from_dict(
        {"id": 1, "text": "test", "created_at": explicit_time, "updated_at": explicit_time}
    )

    assert todo.created_at == explicit_time
    assert todo.updated_at == explicit_time
