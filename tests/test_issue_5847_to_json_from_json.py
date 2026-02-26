"""Tests for to_json/from_json convenience methods (Issue #5847)."""

import json

import pytest

from flywheel.todo import Todo


class TestToJson:
    """Tests for Todo.to_json() method."""

    def test_to_json_returns_valid_json_string(self):
        """to_json() should return a valid JSON string."""
        todo = Todo(id=1, text="Test todo", done=False)
        json_str = todo.to_json()

        # Should be a string
        assert isinstance(json_str, str)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_to_json_contains_all_fields(self):
        """to_json() should include all Todo fields in JSON output."""
        todo = Todo(id=42, text="Buy groceries", done=True)
        json_str = todo.to_json()
        parsed = json.loads(json_str)

        assert parsed["id"] == 42
        assert parsed["text"] == "Buy groceries"
        assert parsed["done"] is True
        assert "created_at" in parsed
        assert "updated_at" in parsed

    def test_to_json_handles_unicode(self):
        """to_json() should properly handle unicode characters."""
        todo = Todo(id=1, text="中文测试 🎉", done=False)
        json_str = todo.to_json()

        # Should not raise
        parsed = json.loads(json_str)
        assert parsed["text"] == "中文测试 🎉"


class TestFromJson:
    """Tests for Todo.from_json() class method."""

    def test_from_json_creates_valid_todo(self):
        """from_json() should create a valid Todo object from JSON string."""
        json_str = '{"id": 1, "text": "Test todo", "done": false}'
        todo = Todo.from_json(json_str)

        assert isinstance(todo, Todo)
        assert todo.id == 1
        assert todo.text == "Test todo"
        assert todo.done is False

    def test_from_json_with_all_fields(self):
        """from_json() should preserve all fields from JSON."""
        json_str = '{"id": 99, "text": "Complete task", "done": true, "created_at": "2024-01-01T00:00:00+00:00", "updated_at": "2024-01-02T00:00:00+00:00"}'
        todo = Todo.from_json(json_str)

        assert todo.id == 99
        assert todo.text == "Complete task"
        assert todo.done is True
        assert todo.created_at == "2024-01-01T00:00:00+00:00"
        assert todo.updated_at == "2024-01-02T00:00:00+00:00"

    def test_from_json_invalid_json_raises_error(self):
        """from_json() should raise ValueError for invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            Todo.from_json("not valid json")

    def test_from_json_non_object_raises_error(self):
        """from_json() should raise ValueError for non-object JSON."""
        with pytest.raises(ValueError, match="must be a JSON object"):
            Todo.from_json('[{"id": 1, "text": "test"}]')


class TestJsonRoundTrip:
    """Tests for JSON serialization round-trip."""

    def test_roundtrip_preserves_all_fields(self):
        """Serializing and deserializing should preserve all fields."""
        original = Todo(id=123, text="Original todo", done=True)
        roundtrip = Todo.from_json(original.to_json())

        assert roundtrip.id == original.id
        assert roundtrip.text == original.text
        assert roundtrip.done == original.done
        assert roundtrip.created_at == original.created_at
        assert roundtrip.updated_at == original.updated_at

    def test_roundtrip_with_unicode(self):
        """Round-trip should preserve unicode characters."""
        original = Todo(id=1, text="日本語テスト 🚀", done=False)
        roundtrip = Todo.from_json(original.to_json())

        assert roundtrip.text == original.text

    def test_roundtrip_with_special_characters(self):
        """Round-trip should preserve special characters."""
        original = Todo(id=1, text='Quote: "test" and newline\n', done=False)
        roundtrip = Todo.from_json(original.to_json())

        assert roundtrip.text == original.text
