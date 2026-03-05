"""Tests for empty timestamp preservation (Issue #7317).

These tests verify that:
1. Todo round-trip (to_dict -> from_dict) preserves empty timestamps
2. Todo.from_dict with explicit empty timestamps preserves them (not auto-filled)
3. New Todo without timestamps still gets auto-filled timestamps
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_preserves_empty_created_at() -> None:
    """Todo.from_dict should preserve explicit empty created_at, not auto-fill."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})
    assert todo.created_at == ""


def test_from_dict_preserves_empty_updated_at() -> None:
    """Todo.from_dict should preserve explicit empty updated_at, not auto-fill."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": ""})
    assert todo.updated_at == ""


def test_from_dict_preserves_both_empty_timestamps() -> None:
    """Todo.from_dict should preserve both empty timestamps."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": "", "updated_at": ""})
    assert todo.created_at == ""
    assert todo.updated_at == ""


def test_round_trip_preserves_empty_timestamps() -> None:
    """Round-trip Todo -> to_dict -> from_dict should preserve empty timestamps."""
    # Create a Todo and manually set empty timestamps (simulating persisted empty state)
    original = Todo(id=1, text="task")
    original.created_at = ""
    original.updated_at = ""

    # Round-trip through dict
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.created_at == ""
    assert restored.updated_at == ""


def test_new_todo_auto_fills_timestamps() -> None:
    """New Todo without explicit timestamps should get auto-filled timestamps."""
    todo = Todo(id=1, text="task")
    assert todo.created_at != ""
    assert todo.updated_at != ""
    assert todo.created_at == todo.updated_at


def test_new_todo_with_explicit_timestamp_preserves_it() -> None:
    """New Todo with explicit timestamp should preserve it."""
    explicit_time = "2024-01-01T00:00:00+00:00"
    todo = Todo(id=1, text="task", created_at=explicit_time)
    assert todo.created_at == explicit_time


def test_from_dict_with_none_timestamp_auto_fills() -> None:
    """Todo.from_dict with missing timestamp should auto-fill (not leave empty)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.created_at != ""
    assert todo.updated_at != ""
