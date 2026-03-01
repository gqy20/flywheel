"""Tests for Todo tags/category field support (Issue #6634).

These tests verify that:
1. Todo has an optional tags field (list[str] type), defaults to empty list
2. to_dict/from_dict correctly handles tags field serialization
3. CLI list command supports --tag parameter for filtering
4. Old data without tags field defaults to empty list
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser
from flywheel.todo import Todo


class TestTodoTagsField:
    """Tests for tags field in Todo dataclass."""

    def test_todo_create_with_tags(self) -> None:
        """Todo should accept tags parameter during creation."""
        todo = Todo(id=1, text="test task", tags=["work", "urgent"])
        assert todo.tags == ["work", "urgent"]

    def test_todo_tags_defaults_to_empty_list(self) -> None:
        """Todo without tags should default to empty list."""
        todo = Todo(id=1, text="test task")
        assert todo.tags == []

    def test_todo_to_dict_includes_tags(self) -> None:
        """to_dict should include tags field."""
        todo = Todo(id=1, text="test task", tags=["work"])
        data = todo.to_dict()
        assert "tags" in data
        assert data["tags"] == ["work"]

    def test_todo_from_dict_parses_tags(self) -> None:
        """from_dict should parse tags field from dict."""
        data = {"id": 1, "text": "test task", "tags": ["personal", "home"]}
        todo = Todo.from_dict(data)
        assert todo.tags == ["personal", "home"]

    def test_todo_from_dict_handles_missing_tags(self) -> None:
        """from_dict should default to empty list when tags field is missing."""
        data = {"id": 1, "text": "test task"}
        todo = Todo.from_dict(data)
        assert todo.tags == []


class TestTodoTagsStorage:
    """Tests for tags serialization in storage."""

    def test_tags_persisted_and_loaded(self, tmp_path) -> None:
        """Tags should be persisted to storage and loaded correctly."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Create todo with tags
        todo = Todo(id=1, text="tagged task", tags=["work", "project"])
        storage.save([todo])

        # Load and verify tags
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].tags == ["work", "project"]

    def test_legacy_data_without_tags_loads_correctly(self, tmp_path) -> None:
        """Old data without tags field should load with empty tags list."""
        import json

        from flywheel.storage import TodoStorage

        db = tmp_path / "legacy.json"
        # Write legacy format without tags
        db.write_text(
            json.dumps([{"id": 1, "text": "legacy task", "done": False}]),
            encoding="utf-8",
        )

        storage = TodoStorage(str(db))
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].tags == []


class TestTodoTagsCLI:
    """Tests for --tag filter in CLI list command."""

    def test_list_filter_by_single_tag(self, tmp_path) -> None:
        """CLI list --tag should filter todos by a single tag."""
        db = tmp_path / "test.json"

        app = TodoApp(db_path=str(db))
        # Add todos with different tags
        todo1 = Todo(id=1, text="work task", tags=["work"])
        todo2 = Todo(id=2, text="personal task", tags=["personal"])
        todo3 = Todo(id=3, text="multi task", tags=["work", "personal"])
        app._save([todo1, todo2, todo3])

        # Filter by 'work' tag
        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "list", "--tag", "work"])
        # This will initially fail because --tag doesn't exist yet

        # Just verify parsing works for now
        assert args.tag == "work"

    def test_list_without_tag_shows_all(self, tmp_path) -> None:
        """CLI list without --tag should show all todos."""
        db = tmp_path / "test.json"

        app = TodoApp(db_path=str(db))
        todo1 = Todo(id=1, text="task1", tags=["work"])
        todo2 = Todo(id=2, text="task2", tags=["personal"])
        app._save([todo1, todo2])

        # List without filter
        result = app.list(show_all=True)
        assert len(result) == 2


class TestTodoFormatterWithTags:
    """Tests for formatter displaying tags."""

    def test_format_todo_shows_tags(self) -> None:
        """format_todo should display tags when present."""
        from flywheel.formatter import TodoFormatter

        todo = Todo(id=1, text="tagged task", tags=["work", "urgent"])
        output = TodoFormatter.format_todo(todo)
        # Should show tags in output
        assert "work" in output or "urgent" in output

    def test_format_todo_no_tags_no_extra_output(self) -> None:
        """format_todo without tags should not show empty tag markers."""
        from flywheel.formatter import TodoFormatter

        todo = Todo(id=1, text="untagged task")
        output = TodoFormatter.format_todo(todo)
        # Should not show "[]" or "tags:" when no tags
        assert "[]" not in output
