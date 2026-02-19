"""Tests for Todo tags/category field (Issue #4414).

These tests verify that:
1. Todo supports optional tags field (default empty tuple)
2. from_dict accepts list or tuple format for tags
3. CLI list supports --tag filter parameter
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command
from flywheel.todo import Todo


class TestTodoTagsField:
    """Tests for tags field on Todo model."""

    def test_todo_supports_tags_field_with_default_empty_tuple(self) -> None:
        """Todo should support tags field with default empty tuple."""
        todo = Todo(id=1, text="task with tags", tags=("work", "urgent"))
        assert todo.tags == ("work", "urgent")

    def test_todo_tags_defaults_to_empty_tuple(self) -> None:
        """Todo tags should default to empty tuple when not provided."""
        todo = Todo(id=1, text="task without tags")
        assert todo.tags == ()

    def test_todo_tags_can_be_single_tag(self) -> None:
        """Todo tags can have a single tag."""
        todo = Todo(id=1, text="single tag task", tags=("personal",))
        assert todo.tags == ("personal",)


class TestTodoFromDictTags:
    """Tests for from_dict accepting tags in list or tuple format."""

    def test_from_dict_accepts_list_format_tags(self) -> None:
        """from_dict should accept tags as list format."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "tags": ["work", "urgent"]
        })
        assert todo.tags == ("work", "urgent")

    def test_from_dict_accepts_tuple_format_tags(self) -> None:
        """from_dict should accept tags as tuple format."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "tags": ("personal",)
        })
        assert todo.tags == ("personal",)

    def test_from_dict_handles_missing_tags_as_empty(self) -> None:
        """from_dict should default missing tags to empty tuple."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.tags == ()

    def test_from_dict_preserves_other_fields_with_tags(self) -> None:
        """from_dict should preserve other fields when tags are present."""
        todo = Todo.from_dict({
            "id": 2,
            "text": "complete task",
            "done": True,
            "tags": ["work"]
        })
        assert todo.id == 2
        assert todo.text == "complete task"
        assert todo.done is True
        assert todo.tags == ("work",)


class TestTodoToDictTags:
    """Tests for to_dict outputting tags."""

    def test_to_dict_includes_tags(self) -> None:
        """to_dict should include tags field."""
        todo = Todo(id=1, text="task", tags=("work", "urgent"))
        data = todo.to_dict()
        assert "tags" in data
        assert data["tags"] == ("work", "urgent")

    def test_to_dict_includes_empty_tags(self) -> None:
        """to_dict should include tags even when empty."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()
        assert "tags" in data
        assert data["tags"] == ()


class TestCliTagFilter:
    """Tests for CLI list --tag filter parameter."""

    def test_list_parser_accepts_tag_argument(self) -> None:
        """CLI parser should accept --tag argument for list command."""
        parser = build_parser()
        args = parser.parse_args(["list", "--tag", "work"])
        assert hasattr(args, "tag")
        assert args.tag == "work"

    def test_list_without_tag_shows_all_todos(self, tmp_path) -> None:
        """list without --tag should show all todos."""
        app = TodoApp(str(tmp_path / "db.json"))

        # Add todos with different tags via direct Todo creation
        # (storage round-trip needed to test CLI filtering)
        storage = app.storage
        todos = [
            Todo(id=1, text="work task", tags=("work",)),
            Todo(id=2, text="personal task", tags=("personal",)),
            Todo(id=3, text="untagged task"),
        ]
        storage.save(todos)

        listed = app.list(show_all=True)
        assert len(listed) == 3

    def test_list_with_tag_filters_by_tag(self, tmp_path) -> None:
        """list --tag work should only show todos with 'work' tag."""
        app = TodoApp(str(tmp_path / "db.json"))

        # Create and save todos with different tags
        storage = app.storage
        todos = [
            Todo(id=1, text="work task 1", tags=("work",)),
            Todo(id=2, text="personal task", tags=("personal",)),
            Todo(id=3, text="work urgent", tags=("work", "urgent")),
            Todo(id=4, text="untagged task"),
        ]
        storage.save(todos)

        # Filter by 'work' tag
        filtered = app.list(show_all=True, tag="work")
        assert len(filtered) == 2
        texts = [t.text for t in filtered]
        assert "work task 1" in texts
        assert "work urgent" in texts
        assert "personal task" not in texts
        assert "untagged task" not in texts

    def test_list_with_tag_no_match_returns_empty(self, tmp_path) -> None:
        """list --tag with non-existent tag should return empty list."""
        app = TodoApp(str(tmp_path / "db.json"))

        storage = app.storage
        todos = [Todo(id=1, text="work task", tags=("work",))]
        storage.save(todos)

        filtered = app.list(show_all=True, tag="nonexistent")
        assert filtered == []

    def test_cli_list_tag_output(self, tmp_path, capsys) -> None:
        """CLI list --tag should filter output correctly."""
        db = str(tmp_path / "cli.json")
        parser = build_parser()

        # First set up data
        from flywheel.storage import TodoStorage
        storage = TodoStorage(db)
        storage.save([
            Todo(id=1, text="work task", tags=("work",)),
            Todo(id=2, text="personal task", tags=("personal",)),
        ])

        # Run list --tag work
        args = parser.parse_args(["--db", db, "list", "--tag", "work"])
        assert run_command(args) == 0
        out = capsys.readouterr().out
        assert "work task" in out
        assert "personal task" not in out
