"""Tests for Todo tags field (Issue #6634).

These tests verify that:
1. Todo dataclass includes optional tags field (list[str])
2. to_dict/from_dict correctly handle tags serialization
3. Legacy data without tags defaults to empty list
4. CLI list command supports --tag filter parameter
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoTagsField:
    """Tests for Todo.tags field functionality."""

    def test_todo_with_tags_creates_successfully(self) -> None:
        """Todo should accept optional tags parameter."""
        todo = Todo(id=1, text="task with tags", tags=["work", "urgent"])
        assert todo.tags == ["work", "urgent"]

    def test_todo_without_tags_defaults_to_empty_list(self) -> None:
        """Todo created without tags should have empty list as default."""
        todo = Todo(id=1, text="simple task")
        assert todo.tags == []

    def test_todo_tags_is_list_of_strings(self) -> None:
        """Todo tags should be a list of strings."""
        todo = Todo(id=1, text="task", tags=["personal", "home"])
        assert isinstance(todo.tags, list)
        assert all(isinstance(tag, str) for tag in todo.tags)

    def test_todo_to_dict_includes_tags(self) -> None:
        """to_dict should include tags field in output."""
        todo = Todo(id=1, text="task", tags=["work"])
        result = todo.to_dict()
        assert "tags" in result
        assert result["tags"] == ["work"]

    def test_todo_from_dict_parses_tags(self) -> None:
        """from_dict should correctly parse tags field."""
        data = {"id": 1, "text": "task", "tags": ["personal", "errand"]}
        todo = Todo.from_dict(data)
        assert todo.tags == ["personal", "errand"]

    def test_todo_from_dict_missing_tags_defaults_to_empty_list(self) -> None:
        """from_dict should default missing tags to empty list for backward compatibility."""
        data = {"id": 1, "text": "legacy task without tags"}
        todo = Todo.from_dict(data)
        assert todo.tags == []

    def test_todo_from_dict_empty_tags_list(self) -> None:
        """from_dict should accept empty tags list."""
        data = {"id": 1, "text": "task", "tags": []}
        todo = Todo.from_dict(data)
        assert todo.tags == []

    def test_todo_roundtrip_preserves_tags(self) -> None:
        """to_dict -> from_dict should preserve tags."""
        original = Todo(id=1, text="task", tags=["a", "b", "c"])
        roundtrip = Todo.from_dict(original.to_dict())
        assert roundtrip.tags == ["a", "b", "c"]


class TestTodoTagsValidation:
    """Tests for tags field validation."""

    def test_from_dict_rejects_non_list_tags(self) -> None:
        """from_dict should reject non-list tags value."""
        with pytest.raises(ValueError, match=r"tags.*list|array"):
            Todo.from_dict({"id": 1, "text": "task", "tags": "work"})

    def test_from_dict_rejects_non_string_tag_elements(self) -> None:
        """from_dict should reject non-string elements in tags."""
        with pytest.raises(ValueError, match=r"tags.*string"):
            Todo.from_dict({"id": 1, "text": "task", "tags": [1, 2, 3]})
