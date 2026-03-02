"""Tests for Todo tags field (Issue #6872).

These tests verify that:
1. Todo dataclass has a tags: tuple[str, ...] field with default empty tuple
2. from_dict converts JSON array to tuple, stripping whitespace and filtering empty strings
3. to_dict converts tuple to JSON array
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoTagsField:
    """Tests for Todo tags field functionality."""

    def test_todo_with_tags_creates_normally(self) -> None:
        """Todo with tags should create normally."""
        todo = Todo(id=1, text="task", tags=("work", "urgent"))
        assert todo.tags == ("work", "urgent")

    def test_todo_default_tags_is_empty_tuple(self) -> None:
        """Todo without tags should default to empty tuple."""
        todo = Todo(id=1, text="task")
        assert todo.tags == ()
        assert isinstance(todo.tags, tuple)

    def test_from_dict_converts_list_to_tuple(self) -> None:
        """from_dict should convert tags list to tuple."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["a", "b"]})
        assert todo.tags == ("a", "b")
        assert isinstance(todo.tags, tuple)

    def test_from_dict_handles_missing_tags(self) -> None:
        """from_dict should handle missing tags field gracefully."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.tags == ()

    def test_from_dict_strips_whitespace_from_tags(self) -> None:
        """from_dict should strip whitespace from tag strings."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["  work  ", " personal "]})
        assert todo.tags == ("work", "personal")

    def test_from_dict_filters_empty_strings_from_tags(self) -> None:
        """from_dict should filter empty strings from tags."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["work", "", "  ", "urgent"]})
        assert todo.tags == ("work", "urgent")

    def test_to_dict_converts_tags_to_list(self) -> None:
        """to_dict should convert tags tuple to list."""
        todo = Todo(id=1, text="task", tags=("work", "urgent"))
        result = todo.to_dict()
        assert result["tags"] == ["work", "urgent"]
        assert isinstance(result["tags"], list)

    def test_to_dict_empty_tags_is_empty_list(self) -> None:
        """to_dict should convert empty tuple to empty list."""
        todo = Todo(id=1, text="task")
        result = todo.to_dict()
        assert result["tags"] == []
        assert isinstance(result["tags"], list)

    def test_roundtrip_preserves_tags(self) -> None:
        """Tags should survive roundtrip through from_dict/to_dict."""
        original = {"id": 1, "text": "task", "tags": ["work", "urgent"]}
        todo = Todo.from_dict(original)
        result = todo.to_dict()
        assert result["tags"] == ["work", "urgent"]
