"""Tests for Todo.to_dict() type precision (Issue #6547).

These tests verify that:
1. to_dict() returns dict[str, Any] with precise type annotation
2. The return value has the correct structure for JSON serialization
3. Type checkers (mypy --strict) can verify the return type
"""

from __future__ import annotations

import json
from typing import get_type_hints

from flywheel.todo import Todo


def test_to_dict_returns_correct_types() -> None:
    """to_dict() should return a dict with correctly typed values."""
    todo = Todo(id=1, text="test task", done=False)
    result = todo.to_dict()

    # Verify each field has the correct type
    assert isinstance(result["id"], int)
    assert isinstance(result["text"], str)
    assert isinstance(result["done"], bool)
    assert isinstance(result["created_at"], str)
    assert isinstance(result["updated_at"], str)


def test_to_dict_json_serializable() -> None:
    """to_dict() return value should be directly JSON serializable."""
    todo = Todo(id=42, text="json test", done=True)
    result = todo.to_dict()

    # Should not raise - validates all values are JSON-compatible
    json_str = json.dumps(result)
    assert isinstance(json_str, str)

    # Round-trip should preserve values
    parsed = json.loads(json_str)
    assert parsed["id"] == 42
    assert parsed["text"] == "json test"
    assert parsed["done"] is True


def test_to_dict_has_all_expected_keys() -> None:
    """to_dict() should return dict with all expected keys."""
    todo = Todo(id=1, text="keys test", done=False)
    result = todo.to_dict()

    expected_keys = {"id", "text", "done", "created_at", "updated_at"}
    assert set(result.keys()) == expected_keys


def test_to_dict_with_custom_timestamps() -> None:
    """to_dict() should preserve custom timestamps."""
    todo = Todo(
        id=1,
        text="timestamps test",
        done=True,
        created_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-02T12:30:45+00:00",
    )
    result = todo.to_dict()

    assert result["created_at"] == "2024-01-01T00:00:00+00:00"
    assert result["updated_at"] == "2024-01-02T12:30:45+00:00"


# Type annotation verification - this test exists to document the expected type
# The actual type checking is done by mypy, but we can at least verify the annotation exists
def test_to_dict_return_type_is_annotated() -> None:
    """to_dict() should have a precise return type annotation (dict[str, Any])."""
    hints = get_type_hints(Todo.to_dict)
    assert "return" in hints, "to_dict() should have a return type annotation"

    # The return type should be dict[str, Any] or similar precise type,
    # not just bare 'dict'
    return_type = hints["return"]
    return_type_str = str(return_type)

    # Should contain 'str' as the key type indicator
    assert "str" in return_type_str, (
        f"Return type should specify string keys, got: {return_type_str}"
    )
