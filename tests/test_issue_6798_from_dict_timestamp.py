"""Tests for timestamp preservation during from_dict deserialization (Issue #6798).

These tests verify that:
1. from_dict with valid created_at preserves the original value
2. from_dict with missing created_at generates a new timestamp
3. storage roundtrip preserves timestamps correctly
"""

from __future__ import annotations

import time

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_from_dict_preserves_existing_created_at() -> None:
    """from_dict should preserve valid created_at timestamp, not overwrite it."""
    original_timestamp = "2025-01-15T10:30:00+00:00"
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": original_timestamp,
        }
    )

    # The original timestamp should be preserved, not overwritten by __post_init__
    assert todo.created_at == original_timestamp


def test_from_dict_preserves_existing_updated_at() -> None:
    """from_dict should preserve valid updated_at timestamp, not overwrite it."""
    original_timestamp = "2025-01-15T11:45:00+00:00"
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "updated_at": original_timestamp,
        }
    )

    # The original timestamp should be preserved
    assert todo.updated_at == original_timestamp


def test_from_dict_generates_timestamp_when_missing() -> None:
    """from_dict should generate new timestamps when they are not provided."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
        }
    )

    # Should have auto-generated timestamps
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_storage_roundtrip_preserves_timestamps(tmp_path) -> None:
    """Storage save/load should preserve original timestamps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a todo and save it
    original_todo = Todo(id=1, text="task")
    original_created_at = original_todo.created_at

    storage.save([original_todo])

    # Wait a tiny bit to ensure any regenerated timestamp would differ
    time.sleep(0.01)

    # Load it back
    loaded = storage.load()
    assert len(loaded) == 1

    # The loaded todo should have the same created_at as the original
    assert loaded[0].created_at == original_created_at


def test_from_dict_handles_none_timestamp_as_missing() -> None:
    """from_dict should treat None timestamp values as missing and generate new ones."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": None,
            "updated_at": None,
        }
    )

    # None should be treated as missing, generating new timestamps
    assert todo.created_at != ""
    assert todo.updated_at != ""
