"""Tests for issue #7317: Todo.__post_init__ empty timestamp handling.

Bug: __post_init__ uses `if not self.created_at` which treats empty string as
falsy, causing from_dict with explicit empty timestamps to be overwritten.

Fix: Change condition to check if the field is the default empty string,
preserving explicit empty strings from persistence layer.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_preserves_empty_created_at() -> None:
    """from_dict with empty created_at should preserve empty string.

    This verifies that persistence layer can store/load todos with empty
    timestamps without __post_init__ overwriting them.
    """
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": ""})
    assert todo.created_at == ""


def test_from_dict_preserves_empty_updated_at() -> None:
    """from_dict with empty updated_at should preserve empty string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": ""})
    assert todo.updated_at == ""


def test_new_todo_auto_fills_timestamps() -> None:
    """New Todo without timestamps should get auto-filled timestamps."""
    todo = Todo(id=1, text="test")
    assert todo.created_at != ""
    assert todo.updated_at != ""
    assert todo.updated_at == todo.created_at


def test_roundtrip_preserves_timestamps() -> None:
    """Todo -> to_dict -> from_dict should preserve timestamps exactly."""
    original = Todo(id=1, text="test", done=True, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-02T00:00:00Z")
    roundtrip = Todo.from_dict(original.to_dict())

    assert roundtrip.created_at == original.created_at
    assert roundtrip.updated_at == original.updated_at


def test_roundtrip_preserves_empty_timestamps() -> None:
    """Round-trip should preserve empty timestamps (edge case)."""
    data = {"id": 1, "text": "test", "done": False, "created_at": "", "updated_at": ""}
    todo = Todo.from_dict(data)
    roundtrip = Todo.from_dict(todo.to_dict())

    assert todo.created_at == ""
    assert todo.updated_at == ""
    assert roundtrip.created_at == ""
    assert roundtrip.updated_at == ""


def test_from_dict_with_none_timestamp_gets_empty_string() -> None:
    """from_dict with None timestamp should convert to empty string (not auto-fill)."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})
    assert todo.created_at == ""
