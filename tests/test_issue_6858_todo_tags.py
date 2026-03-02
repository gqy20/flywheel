"""Tests for Todo tags field support (Issue #6858).

These tests verify that:
1. Todo dataclass includes tags field, defaulting to empty list
2. from_dict correctly parses tags field as string list
3. to_dict serializes tags field
4. tags elements are deduplicated and whitespace stripped
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoTagsField:
    """Tests for the tags field in Todo dataclass."""

    def test_todo_default_tags_is_empty_list(self) -> None:
        """Todo should have an empty list as default tags."""
        todo = Todo(id=1, text="task")
        assert todo.tags == []

    def test_from_dict_parses_valid_tags_list(self) -> None:
        """from_dict should correctly parse a valid tags list."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["work", "personal"]})
        assert todo.tags == ["work", "personal"]

    def test_from_dict_handles_missing_tags(self) -> None:
        """from_dict should default to empty list when tags is missing."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.tags == []

    def test_from_dict_rejects_non_list_tags(self) -> None:
        """from_dict should reject non-list types for tags field."""
        with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list"):
            Todo.from_dict({"id": 1, "text": "task", "tags": "work"})

    def test_from_dict_rejects_non_string_elements_in_tags(self) -> None:
        """from_dict should reject non-string elements in tags list."""
        with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*string"):
            Todo.from_dict({"id": 1, "text": "task", "tags": [1, 2]})

    def test_from_dict_strips_whitespace_from_tags(self) -> None:
        """from_dict should strip whitespace from tag elements."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["  work  ", " personal "]})
        assert todo.tags == ["work", "personal"]

    def test_from_dict_deduplicates_tags(self) -> None:
        """from_dict should deduplicate tags."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["work", "work", "personal"]})
        assert todo.tags == ["work", "personal"]

    def test_to_dict_includes_tags(self) -> None:
        """to_dict should include tags field in serialization."""
        todo = Todo(id=1, text="task", tags=["work", "personal"])
        data = todo.to_dict()
        assert "tags" in data
        assert data["tags"] == ["work", "personal"]

    def test_to_dict_includes_empty_tags(self) -> None:
        """to_dict should include empty tags list in serialization."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()
        assert "tags" in data
        assert data["tags"] == []
