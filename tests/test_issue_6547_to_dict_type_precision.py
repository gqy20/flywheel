"""Tests for Todo.to_dict() return type precision (Issue #6547).

These tests verify that:
1. to_dict() returns dict[str, Any] with fully specified type parameters
2. The return value contains correct key types: id (int), text (str), done (bool), timestamps (str)
3. The return value is JSON serializable
"""

from __future__ import annotations

import json
from typing import get_type_hints

from flywheel.todo import Todo


def test_to_dict_return_type_annotation_is_precise() -> None:
    """to_dict() should have return type dict[str, Any] not bare dict."""
    hints = get_type_hints(Todo.to_dict)
    return_type = hints.get("return")

    # The return type should be dict[str, Any] or dict[str, int | str | bool]
    # It should NOT be the bare `dict` type without parameters
    assert return_type is not dict, (
        "to_dict() return type should be dict[str, Any] or similar, not bare dict"
    )

    # Check that it's a dict with type parameters
    type_str = str(return_type)
    assert "dict" in type_str.lower() and "[" in type_str, (
        f"to_dict() return type should be dict[K, V], got: {return_type}"
    )


def test_to_dict_returns_correct_value_types() -> None:
    """to_dict() should return a dict with correct value types for all fields."""
    todo = Todo(id=1, text="test task", done=False)
    result = todo.to_dict()

    # Verify key types
    assert isinstance(result["id"], int), f"id should be int, got {type(result['id'])}"
    assert isinstance(result["text"], str), f"text should be str, got {type(result['text'])}"
    assert isinstance(result["done"], bool), f"done should be bool, got {type(result['done'])}"
    assert isinstance(result["created_at"], str), (
        f"created_at should be str, got {type(result['created_at'])}"
    )
    assert isinstance(result["updated_at"], str), (
        f"updated_at should be str, got {type(result['updated_at'])}"
    )


def test_to_dict_returns_json_serializable() -> None:
    """to_dict() return value should be directly JSON serializable."""
    todo = Todo(id=42, text="JSON test", done=True)
    result = todo.to_dict()

    # Should not raise - verifies all values are JSON-compatible types
    json_str = json.dumps(result)
    assert isinstance(json_str, str)

    # Should be able to round-trip
    parsed = json.loads(json_str)
    assert parsed["id"] == 42
    assert parsed["text"] == "JSON test"
    assert parsed["done"] is True


def test_to_dict_contains_all_expected_keys() -> None:
    """to_dict() should contain all expected keys from the dataclass."""
    todo = Todo(id=1, text="test")
    result = todo.to_dict()

    expected_keys = {"id", "text", "done", "created_at", "updated_at"}
    assert set(result.keys()) == expected_keys, (
        f"Expected keys {expected_keys}, got {set(result.keys())}"
    )
