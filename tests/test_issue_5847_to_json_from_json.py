"""Tests for Todo.to_json/from_json convenience methods (Issue #5847).

These tests verify that:
1. to_json() returns a valid JSON string
2. from_json(json_str) correctly reconstructs a Todo object
3. Round-trip serialization preserves all object fields
"""

from __future__ import annotations

import json

from flywheel.todo import Todo


def test_todo_to_json_returns_valid_json_string() -> None:
    """to_json() should return a valid JSON string."""
    todo = Todo(id=1, text="buy milk", done=False)
    json_str = todo.to_json()

    # Should be a string
    assert isinstance(json_str, str)

    # Should be valid JSON that can be parsed
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


def test_todo_to_json_contains_all_fields() -> None:
    """to_json() should include all fields in the JSON output."""
    todo = Todo(id=1, text="buy milk", done=True)
    json_str = todo.to_json()
    parsed = json.loads(json_str)

    assert parsed["id"] == 1
    assert parsed["text"] == "buy milk"
    assert parsed["done"] is True
    assert "created_at" in parsed
    assert "updated_at" in parsed


def test_todo_from_json_reconstructs_object() -> None:
    """from_json(json_str) should correctly reconstruct a Todo object."""
    json_str = '{"id": 2, "text": "do laundry", "done": false, "created_at": "2024-01-01T00:00:00+00:00", "updated_at": "2024-01-01T00:00:00+00:00"}'
    todo = Todo.from_json(json_str)

    assert todo.id == 2
    assert todo.text == "do laundry"
    assert todo.done is False
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
    assert todo.updated_at == "2024-01-01T00:00:00+00:00"


def test_todo_from_json_with_minimal_fields() -> None:
    """from_json(json_str) should work with minimal required fields."""
    json_str = '{"id": 42, "text": "minimal todo"}'
    todo = Todo.from_json(json_str)

    assert todo.id == 42
    assert todo.text == "minimal todo"
    assert todo.done is False


def test_todo_roundtrip_preserves_all_fields() -> None:
    """Round-trip serialization should preserve all object fields."""
    original = Todo(id=1, text="test task", done=True)
    roundtrip = Todo.from_json(original.to_json())

    assert roundtrip.id == original.id
    assert roundtrip.text == original.text
    assert roundtrip.done == original.done
    assert roundtrip.created_at == original.created_at
    assert roundtrip.updated_at == original.updated_at


def test_todo_to_json_handles_unicode() -> None:
    """to_json() should properly handle Unicode characters."""
    todo = Todo(id=1, text="中文测试 日本語 한국어")
    json_str = todo.to_json()
    parsed = json.loads(json_str)

    assert parsed["text"] == "中文测试 日本語 한국어"


def test_todo_to_json_handles_special_characters() -> None:
    """to_json() should properly handle special characters."""
    todo = Todo(id=1, text='text with "quotes" and \\backslash')
    json_str = todo.to_json()

    # Should be valid JSON
    parsed = json.loads(json_str)
    assert parsed["text"] == 'text with "quotes" and \\backslash'


def test_todo_from_json_raises_on_invalid_json() -> None:
    """from_json(json_str) should raise ValueError on invalid JSON."""
    invalid_json = "not a valid json string"

    try:
        Todo.from_json(invalid_json)
        raise AssertionError("Expected ValueError for invalid JSON")
    except ValueError:
        pass  # Expected


def test_todo_from_json_raises_on_missing_required_field() -> None:
    """from_json(json_str) should raise ValueError on missing required fields."""
    json_without_id = '{"text": "missing id"}'

    try:
        Todo.from_json(json_without_id)
        raise AssertionError("Expected ValueError for missing id")
    except ValueError:
        pass  # Expected
