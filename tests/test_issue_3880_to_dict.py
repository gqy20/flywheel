"""Tests for to_dict() serialization (Issue #3880).

These tests verify that:
1. to_dict() returns a dict with expected keys: id, text, done, created_at, updated_at
2. to_dict() output can be passed to from_dict() for round-trip equality
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_to_dict_returns_expected_keys() -> None:
    """to_dict() should return dict with all expected keys."""
    todo = Todo(id=1, text="test task")
    result = todo.to_dict()

    assert set(result.keys()) == {"id", "text", "done", "created_at", "updated_at"}
    assert result["id"] == 1
    assert result["text"] == "test task"
    assert result["done"] is False
    assert isinstance(result["created_at"], str)
    assert isinstance(result["updated_at"], str)
    assert len(result["created_at"]) > 0
    assert len(result["updated_at"]) > 0


def test_to_dict_includes_done_status() -> None:
    """to_dict() should correctly serialize the done field."""
    todo = Todo(id=1, text="done task", done=True)
    result = todo.to_dict()

    assert result["done"] is True


def test_to_dict_roundtrip_via_from_dict() -> None:
    """to_dict() output should be usable by from_dict() for round-trip serialization."""
    original = Todo(id=1, text="roundtrip test", done=True)
    serialized = original.to_dict()
    restored = Todo.from_dict(serialized)

    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_to_dict_roundtrip_preserves_all_fields() -> None:
    """to_dict() roundtrip should preserve all fields including timestamps."""
    original = Todo(id=42, text="preserve all fields", done=False)
    original.mark_done()  # This changes done to True and updates updated_at

    serialized = original.to_dict()
    restored = Todo.from_dict(serialized)

    assert restored.id == 42
    assert restored.text == "preserve all fields"
    assert restored.done is True
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at
