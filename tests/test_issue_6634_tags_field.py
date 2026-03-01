"""Tests for Todo tags/category field support (Issue #6634).

These tests verify that:
1. Todo contains optional tags: list[str] field, defaulting to empty list
2. to_dict/from_dict correctly handles tags field
3. CLI list command supports --tag parameter for filtering
4. Old data without tags field defaults to empty list
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoTagsField:
    """Tests for the tags field in Todo dataclass."""

    def test_todo_create_with_tags(self) -> None:
        """Todo should accept tags parameter with list of strings."""
        todo = Todo(id=1, text="task with tags", tags=["work", "urgent"])
        assert todo.tags == ["work", "urgent"]

    def test_todo_create_without_tags_defaults_to_empty_list(self) -> None:
        """Todo created without tags should default to empty list."""
        todo = Todo(id=1, text="task without tags")
        assert todo.tags == []

    def test_todo_tags_is_list_of_strings(self) -> None:
        """Todo tags should be a list of strings."""
        todo = Todo(id=1, text="task", tags=["personal", "home"])
        assert isinstance(todo.tags, list)
        assert all(isinstance(tag, str) for tag in todo.tags)

    def test_todo_tags_can_be_empty(self) -> None:
        """Todo tags can be explicitly set to empty list."""
        todo = Todo(id=1, text="task", tags=[])
        assert todo.tags == []


class TestTodoTagsSerialization:
    """Tests for tags field serialization/deserialization."""

    def test_to_dict_includes_tags(self) -> None:
        """to_dict should include tags field."""
        todo = Todo(id=1, text="task", tags=["work", "project"])
        data = todo.to_dict()

        assert "tags" in data
        assert data["tags"] == ["work", "project"]

    def test_to_dict_includes_empty_tags(self) -> None:
        """to_dict should include tags field even when empty."""
        todo = Todo(id=1, text="task", tags=[])
        data = todo.to_dict()

        assert "tags" in data
        assert data["tags"] == []

    def test_from_dict_parses_tags_field(self) -> None:
        """from_dict should correctly parse tags field."""
        data = {"id": 1, "text": "task", "tags": ["work", "urgent"]}
        todo = Todo.from_dict(data)

        assert todo.tags == ["work", "urgent"]

    def test_from_dict_handles_missing_tags_defaults_to_empty(self) -> None:
        """from_dict should default tags to empty list when field is missing."""
        # This tests backward compatibility with old data
        data = {"id": 1, "text": "old task without tags"}
        todo = Todo.from_dict(data)

        assert todo.tags == []

    def test_from_dict_handles_empty_tags_list(self) -> None:
        """from_dict should handle explicit empty tags list."""
        data = {"id": 1, "text": "task", "tags": []}
        todo = Todo.from_dict(data)

        assert todo.tags == []

    def test_roundtrip_preserves_tags(self) -> None:
        """Tags should survive to_dict -> from_dict roundtrip."""
        original = Todo(id=1, text="task", tags=["work", "personal"])
        data = original.to_dict()
        restored = Todo.from_dict(data)

        assert restored.tags == ["work", "personal"]

    def test_from_dict_rejects_non_list_tags(self) -> None:
        """from_dict should reject non-list values for tags field."""
        with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list"):
            Todo.from_dict({"id": 1, "text": "task", "tags": "not-a-list"})

    def test_from_dict_rejects_non_string_tag_items(self) -> None:
        """from_dict should reject non-string items in tags list."""
        with pytest.raises(ValueError, match=r"invalid.*tag|tag.*string"):
            Todo.from_dict({"id": 1, "text": "task", "tags": [1, 2, 3]})


class TestTodoTagsCLI:
    """Tests for CLI --tag filtering."""

    def test_list_with_tag_filter(self, tmp_path) -> None:
        """list command with --tag should filter todos by tag."""
        import json

        from flywheel.cli import TodoApp

        db = tmp_path / "test.json"
        # Create test data with different tags
        db.write_text(
            json.dumps(
                [
                    {"id": 1, "text": "work task", "done": False, "tags": ["work"]},
                    {"id": 2, "text": "personal task", "done": False, "tags": ["personal"]},
                    {"id": 3, "text": "urgent work", "done": False, "tags": ["work", "urgent"]},
                ]
            ),
            encoding="utf-8",
        )

        app = TodoApp(db_path=str(db))
        # Filter by 'work' tag
        filtered = app.list(tag="work")

        assert len(filtered) == 2
        assert all("work" in t.tags for t in filtered)

    def test_list_without_tag_filter_returns_all(self, tmp_path) -> None:
        """list command without --tag should return all todos."""
        import json

        from flywheel.cli import TodoApp

        db = tmp_path / "test.json"
        db.write_text(
            json.dumps(
                [
                    {"id": 1, "text": "task 1", "done": False, "tags": ["work"]},
                    {"id": 2, "text": "task 2", "done": False, "tags": ["personal"]},
                ]
            ),
            encoding="utf-8",
        )

        app = TodoApp(db_path=str(db))
        all_todos = app.list()

        assert len(all_todos) == 2

    def test_list_tag_filter_with_pending(self, tmp_path) -> None:
        """list command should support combining --tag with --pending."""
        import json

        from flywheel.cli import TodoApp

        db = tmp_path / "test.json"
        db.write_text(
            json.dumps(
                [
                    {"id": 1, "text": "pending work", "done": False, "tags": ["work"]},
                    {"id": 2, "text": "done work", "done": True, "tags": ["work"]},
                    {"id": 3, "text": "pending personal", "done": False, "tags": ["personal"]},
                ]
            ),
            encoding="utf-8",
        )

        app = TodoApp(db_path=str(db))
        # Filter by 'work' tag and only pending
        filtered = app.list(show_all=False, tag="work")

        assert len(filtered) == 1
        assert filtered[0].id == 1

    def test_list_tag_filter_no_matches(self, tmp_path) -> None:
        """list command with --tag that matches nothing should return empty list."""
        import json

        from flywheel.cli import TodoApp

        db = tmp_path / "test.json"
        db.write_text(
            json.dumps(
                [
                    {"id": 1, "text": "task", "done": False, "tags": ["work"]},
                ]
            ),
            encoding="utf-8",
        )

        app = TodoApp(db_path=str(db))
        filtered = app.list(tag="nonexistent")

        assert len(filtered) == 0
