"""Tests for Todo.to_dict() return type precision (Issue #6547).

These tests verify that:
1. to_dict() returns dict[str, Any] with precise type annotation
2. The return value has correct key types (id: int, text: str, done: bool, etc.)
3. The return value is JSON serializable
"""

from __future__ import annotations

import json
from typing import get_type_hints

from flywheel.todo import Todo


def test_to_dict_returns_correct_types() -> None:
    """to_dict() should return a dict with correct value types."""
    todo = Todo(id=1, text="test task", done=False)
    result = todo.to_dict()

    # Verify key types
    assert isinstance(result["id"], int)
    assert isinstance(result["text"], str)
    assert isinstance(result["done"], bool)
    assert isinstance(result["created_at"], str)
    assert isinstance(result["updated_at"], str)


def test_to_dict_return_type_annotation_is_precise() -> None:
    """to_dict() should have precise return type annotation (dict[str, Any])."""
    hints = get_type_hints(Todo.to_dict)

    assert "return" in hints, "to_dict should have a return type annotation"

    return_type = hints["return"]
    # The return type should be dict[str, Any] or dict[str, int | str | bool]
    # Not just bare 'dict'
    type_str = str(return_type)

    # Check that it's not just a bare dict
    assert "dict" in type_str.lower(), f"Return type should be dict, got: {return_type}"

    # Check for type parameters (should have [str, ...] form)
    # This ensures we have dict[str, Any] or dict[str, ...] not just dict
    assert "[" in type_str, (
        f"Return type should have type parameters like dict[str, Any], got: {return_type}"
    )


def test_to_dict_json_serializable() -> None:
    """to_dict() return value should be directly JSON serializable."""
    todo = Todo(id=1, text="test task", done=True)
    result = todo.to_dict()

    # Should not raise when serializing to JSON
    json_str = json.dumps(result)
    assert isinstance(json_str, str)

    # Should be able to deserialize back
    loaded = json.loads(json_str)
    assert loaded["id"] == 1
    assert loaded["text"] == "test task"
    assert loaded["done"] is True


def test_to_dict_contains_all_fields() -> None:
    """to_dict() should include all Todo fields."""
    todo = Todo(id=42, text="complete task", done=True)
    result = todo.to_dict()

    expected_keys = {"id", "text", "done", "created_at", "updated_at"}
    assert set(result.keys()) == expected_keys
