"""Tests for to_json/from_json convenience methods (Issue #5847)."""

from __future__ import annotations

import json

import pytest

from flywheel.todo import Todo


def test_to_json_returns_valid_json_string() -> None:
    """to_json() should return a valid JSON string with all fields."""
    todo = Todo(id=1, text="test todo", done=True)

    json_str = todo.to_json()

    # Should be a string
    assert isinstance(json_str, str)

    # Should be valid JSON
    parsed = json.loads(json_str)
    assert parsed["id"] == 1
    assert parsed["text"] == "test todo"
    assert parsed["done"] is True
    assert "created_at" in parsed
    assert "updated_at" in parsed


def test_from_json_restores_todo_object() -> None:
    """from_json(json_str) should correctly restore a Todo object."""
    json_str = '{"id": 42, "text": "restored todo", "done": true, "created_at": "2024-01-01T00:00:00+00:00", "updated_at": "2024-01-02T00:00:00+00:00"}'

    todo = Todo.from_json(json_str)

    assert todo.id == 42
    assert todo.text == "restored todo"
    assert todo.done is True
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
    assert todo.updated_at == "2024-01-02T00:00:00+00:00"


def test_roundtrip_to_json_from_json_preserves_object() -> None:
    """Todo.from_json(original.to_json()) should produce an equivalent object."""
    original = Todo(id=99, text="roundtrip test", done=False)

    # Roundtrip: to_json -> from_json
    restored = Todo.from_json(original.to_json())

    # All fields should match
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_to_json_handles_unicode() -> None:
    """to_json() should properly handle Unicode characters."""
    todo = Todo(id=1, text="测试中文 🎉")

    json_str = todo.to_json()

    # Should not raise, and Unicode should be preserved
    parsed = json.loads(json_str)
    assert parsed["text"] == "测试中文 🎉"


def test_from_json_raises_on_invalid_json() -> None:
    """from_json() should raise ValueError on invalid JSON string."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        Todo.from_json("not valid json")


def test_from_json_raises_on_missing_required_fields() -> None:
    """from_json() should raise ValueError when required fields are missing."""
    with pytest.raises(ValueError, match="Missing required field"):
        Todo.from_json('{"id": 1}')


def test_from_json_uses_defaults_for_optional_fields() -> None:
    """from_json() should use defaults for optional fields when not provided."""
    json_str = '{"id": 1, "text": "minimal"}'

    todo = Todo.from_json(json_str)

    assert todo.id == 1
    assert todo.text == "minimal"
    assert todo.done is False
