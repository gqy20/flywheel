"""Tests for Todo.to_dict() method (Issue #3880).

These tests verify that:
1. to_dict() returns a dict with all expected keys
2. to_dict() output can be passed to from_dict() for round-trip serialization
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_to_dict_returns_expected_keys() -> None:
    """to_dict() should return a dict with keys: id, text, done, created_at, updated_at."""
    todo = Todo(id=1, text="test task", done=True)
    result = todo.to_dict()

    expected_keys = {"id", "text", "done", "created_at", "updated_at"}
    assert set(result.keys()) == expected_keys, (
        f"Expected keys {expected_keys}, got {set(result.keys())}"
    )


def test_to_dict_returns_correct_field_values() -> None:
    """to_dict() should return correct values for each field."""
    todo = Todo(id=42, text="sample task", done=False)
    result = todo.to_dict()

    assert result["id"] == 42
    assert result["text"] == "sample task"
    assert result["done"] is False
    assert isinstance(result["created_at"], str)
    assert isinstance(result["updated_at"], str)


def test_to_dict_roundtrip_via_from_dict() -> None:
    """to_dict() output should be usable in from_dict() for round-trip equality."""
    original = Todo(id=99, text="roundtrip test", done=True)

    # Serialize via to_dict()
    serialized = original.to_dict()

    # Deserialize via from_dict()
    restored = Todo.from_dict(serialized)

    # Verify all fields match
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_to_dict_roundtrip_preserves_timestamps() -> None:
    """to_dict() -> from_dict() should preserve timestamp fields exactly."""
    original = Todo(id=1, text="timestamp test")
    original.created_at = "2024-01-15T10:30:00+00:00"
    original.updated_at = "2024-01-16T14:45:00+00:00"

    serialized = original.to_dict()
    restored = Todo.from_dict(serialized)

    assert restored.created_at == "2024-01-15T10:30:00+00:00"
    assert restored.updated_at == "2024-01-16T14:45:00+00:00"
