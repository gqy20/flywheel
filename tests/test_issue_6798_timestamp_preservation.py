"""Tests for timestamp preservation during deserialization (Issue #6799).

These tests verify that:
1. from_dict preserves valid created_at timestamps
2. from_dict generates new timestamps when created_at is missing
3. Storage roundtrip preserves timestamps correctly
"""

from __future__ import annotations

import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_from_dict_preserves_valid_created_at() -> None:
    """from_dict should preserve the original created_at timestamp."""
    original_timestamp = "2025-01-15T10:30:00+00:00"
    todo = Todo.from_dict(
        {"id": 1, "text": "test task", "created_at": original_timestamp}
    )

    assert todo.created_at == original_timestamp


def test_from_dict_preserves_valid_updated_at() -> None:
    """from_dict should preserve the original updated_at timestamp."""
    original_timestamp = "2025-01-15T12:45:00+00:00"
    todo = Todo.from_dict(
        {"id": 1, "text": "test task", "updated_at": original_timestamp}
    )

    assert todo.updated_at == original_timestamp


def test_from_dict_generates_created_at_when_missing() -> None:
    """from_dict should generate a new created_at when not provided."""
    todo = Todo.from_dict({"id": 1, "text": "test task"})

    # Should have a non-empty timestamp
    assert todo.created_at != ""
    assert len(todo.created_at) > 0


def test_from_dict_generates_created_at_when_empty_string() -> None:
    """from_dict should generate a new created_at when empty string is provided."""
    todo = Todo.from_dict({"id": 1, "text": "test task", "created_at": ""})

    # Should have a non-empty timestamp (empty string triggers generation)
    assert todo.created_at != ""
    assert len(todo.created_at) > 0


def test_from_dict_generates_timestamp_when_none() -> None:
    """from_dict should generate a new created_at when None is provided."""
    todo = Todo.from_dict({"id": 1, "text": "test task", "created_at": None})

    # Should have a non-empty timestamp (None triggers generation)
    assert todo.created_at != ""
    assert len(todo.created_at) > 0


def test_storage_roundtrip_preserves_created_at(tmp_path) -> None:
    """Storage save/load roundtrip should preserve created_at timestamp."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save a todo
    todo = Todo(id=1, text="test task")
    original_created_at = todo.created_at

    storage.save([todo])

    # Small delay to ensure any timestamp difference would be visible
    time.sleep(0.01)

    # Load back and verify timestamp is preserved
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].created_at == original_created_at


def test_storage_roundtrip_preserves_updated_at(tmp_path) -> None:
    """Storage save/load roundtrip should preserve updated_at timestamp."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a todo and modify it to set updated_at
    todo = Todo(id=1, text="test task")
    todo.mark_done()
    original_updated_at = todo.updated_at

    storage.save([todo])

    # Small delay to ensure any timestamp difference would be visible
    time.sleep(0.01)

    # Load back and verify timestamp is preserved
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].updated_at == original_updated_at


def test_storage_roundtrip_preserves_both_timestamps(tmp_path) -> None:
    """Storage save/load roundtrip should preserve both timestamps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a todo and modify it to have different created_at and updated_at
    todo = Todo(id=1, text="test task")
    original_created_at = todo.created_at
    time.sleep(0.01)
    todo.mark_done()
    original_updated_at = todo.updated_at

    # Verify they're different before saving
    assert original_updated_at > original_created_at

    storage.save([todo])

    # Load back and verify both timestamps are preserved
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].created_at == original_created_at
    assert loaded[0].updated_at == original_updated_at
