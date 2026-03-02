"""Tests for timestamp preservation during from_dict deserialization (Issue #6798).

These tests verify that:
1. from_dict with valid created_at preserves the original value
2. from_dict with missing created_at generates a new timestamp
3. storage roundtrip preserves timestamps correctly
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_from_dict_preserves_valid_created_at() -> None:
    """from_dict should preserve valid created_at timestamp."""
    original_timestamp = "2024-01-15T10:30:00+00:00"
    data = {
        "id": 1,
        "text": "test task",
        "done": False,
        "created_at": original_timestamp,
        "updated_at": "2024-01-15T11:00:00+00:00",
    }

    todo = Todo.from_dict(data)

    assert todo.created_at == original_timestamp, (
        f"from_dict should preserve original created_at, "
        f"expected {original_timestamp!r}, got {todo.created_at!r}"
    )


def test_from_dict_generates_timestamp_when_missing() -> None:
    """from_dict should generate new timestamp when created_at is missing."""
    data = {
        "id": 1,
        "text": "test task",
        "done": False,
    }

    todo = Todo.from_dict(data)

    # Should have generated a timestamp (non-empty)
    assert todo.created_at, "from_dict should generate created_at when missing"
    assert len(todo.created_at) > 0, "generated created_at should not be empty"


def test_from_dict_generates_timestamp_when_empty_string() -> None:
    """from_dict should generate new timestamp when created_at is empty string."""
    data = {
        "id": 1,
        "text": "test task",
        "done": False,
        "created_at": "",
        "updated_at": "",
    }

    todo = Todo.from_dict(data)

    # Empty string should trigger timestamp generation
    assert todo.created_at, "from_dict should generate created_at when empty string"


def test_storage_roundtrip_preserves_timestamp() -> None:
    """Storage save/load roundtrip should preserve created_at timestamp."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = TodoStorage(path=str(Path(tmpdir) / "test.json"))

        # Create a todo with a specific timestamp
        original_timestamp = "2024-01-15T10:30:00+00:00"
        todo = Todo(
            id=1,
            text="test task",
            done=False,
            created_at=original_timestamp,
            updated_at=original_timestamp,
        )

        # Save and reload
        storage.save([todo])
        loaded_todos = storage.load()

        assert len(loaded_todos) == 1
        loaded_todo = loaded_todos[0]

        assert loaded_todo.created_at == original_timestamp, (
            f"storage roundtrip should preserve created_at, "
            f"expected {original_timestamp!r}, got {loaded_todo.created_at!r}"
        )


def test_from_dict_preserves_valid_updated_at() -> None:
    """from_dict should preserve valid updated_at timestamp."""
    original_updated = "2024-01-15T11:00:00+00:00"
    data = {
        "id": 1,
        "text": "test task",
        "done": False,
        "created_at": "2024-01-15T10:30:00+00:00",
        "updated_at": original_updated,
    }

    todo = Todo.from_dict(data)

    assert todo.updated_at == original_updated, (
        f"from_dict should preserve original updated_at, "
        f"expected {original_updated!r}, got {todo.updated_at!r}"
    )
