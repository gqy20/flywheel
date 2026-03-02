"""Tests for Todo tags field (Issue #6858).

These tests verify that:
1. Todo dataclass includes tags field with default empty list
2. from_dict correctly parses tags field as string list
3. from_dict rejects non-list types for tags
4. to_dict serializes tags field
5. Tags are normalized (stripped whitespace, deduplicated)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoTagsDefault:
    """Tests for default tags behavior."""

    def test_todo_default_tags_is_empty_list(self) -> None:
        """Todo created without tags should have empty list as default."""
        todo = Todo(id=1, text="buy milk")
        assert todo.tags == []

    def test_todo_can_be_created_with_tags(self) -> None:
        """Todo can be created with explicit tags list."""
        todo = Todo(id=1, text="buy milk", tags=["work", "personal"])
        assert todo.tags == ["work", "personal"]

    def test_todo_tags_are_independent_per_instance(self) -> None:
        """Each Todo instance should have its own tags list (not shared)."""
        todo1 = Todo(id=1, text="task1", tags=["work"])
        todo2 = Todo(id=2, text="task2", tags=["personal"])
        assert todo1.tags == ["work"]
        assert todo2.tags == ["personal"]


class TestTodoFromDictTags:
    """Tests for from_dict parsing of tags field."""

    def test_from_dict_parses_valid_tags_list(self) -> None:
        """from_dict should correctly parse a valid tags list."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "tags": ["work", "personal"]
        })
        assert todo.tags == ["work", "personal"]

    def test_from_dict_handles_missing_tags_as_empty(self) -> None:
        """from_dict should default to empty list when tags field is missing."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.tags == []

    def test_from_dict_handles_empty_tags_list(self) -> None:
        """from_dict should accept an empty tags list."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": []})
        assert todo.tags == []

    def test_from_dict_rejects_non_list_tags_string(self) -> None:
        """from_dict should reject string type for tags field."""
        with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list|'tags'.*type"):
            Todo.from_dict({"id": 1, "text": "task", "tags": "work"})

    def test_from_dict_rejects_non_list_tags_int(self) -> None:
        """from_dict should reject integer type for tags field."""
        with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list|'tags'.*type"):
            Todo.from_dict({"id": 1, "text": "task", "tags": 123})

    def test_from_dict_rejects_non_list_tags_dict(self) -> None:
        """from_dict should reject dict type for tags field."""
        with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list|'tags'.*type"):
            Todo.from_dict({"id": 1, "text": "task", "tags": {"work": True}})

    def test_from_dict_normalizes_tags_whitespace(self) -> None:
        """from_dict should strip whitespace from tag strings."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "tags": ["  work  ", " personal ", "urgent"]
        })
        assert todo.tags == ["work", "personal", "urgent"]

    def test_from_dict_deduplicates_tags(self) -> None:
        """from_dict should remove duplicate tags."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "tags": ["work", "personal", "work", "urgent", "personal"]
        })
        # Deduplicated, order may vary but should only have unique values
        assert len(todo.tags) == 3
        assert set(todo.tags) == {"work", "personal", "urgent"}


class TestTodoToDictTags:
    """Tests for to_dict serialization of tags field."""

    def test_to_dict_includes_tags(self) -> None:
        """to_dict should include the tags field in output."""
        todo = Todo(id=1, text="task", tags=["work", "personal"])
        data = todo.to_dict()
        assert "tags" in data
        assert data["tags"] == ["work", "personal"]

    def test_to_dict_includes_empty_tags(self) -> None:
        """to_dict should include tags field even when empty."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()
        assert "tags" in data
        assert data["tags"] == []


class TestTodoTagsRoundTrip:
    """Tests for serialization round-trip."""

    def test_roundtrip_preserves_tags(self) -> None:
        """Tags should survive to_dict -> from_dict round trip."""
        original = Todo(id=1, text="task", tags=["work", "personal"])
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.tags == ["work", "personal"]
