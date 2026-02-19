"""Tests for Issue #4414: Todo tags/category field support.

These tests verify that:
1. Todo supports optional tags field (default empty tuple)
2. from_dict accepts tags as list or tuple format
3. to_dict returns tags as list format
4. CLI list command supports --tag filtering
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoTagsField:
    """Tests for Todo tags field in the data model."""

    def test_todo_with_tags_creates_successfully(self) -> None:
        """Todo(id=1, text='a', tags=('work',)) should create normally."""
        todo = Todo(id=1, text="a", tags=("work",))
        assert todo.tags == ("work",)

    def test_todo_tags_defaults_to_empty_tuple(self) -> None:
        """Todo should have empty tuple as default for tags."""
        todo = Todo(id=1, text="task")
        assert todo.tags == ()

    def test_todo_with_multiple_tags(self) -> None:
        """Todo should support multiple tags."""
        todo = Todo(id=1, text="task", tags=("work", "urgent", "project-a"))
        assert todo.tags == ("work", "urgent", "project-a")

    def test_todo_to_dict_includes_tags_as_list(self) -> None:
        """to_dict should return tags as a list."""
        todo = Todo(id=1, text="task", tags=("work", "urgent"))
        data = todo.to_dict()
        assert data["tags"] == ["work", "urgent"]

    def test_todo_to_dict_includes_empty_tags_list(self) -> None:
        """to_dict should include empty list for todos without tags."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()
        assert data["tags"] == []


class TestTodoFromDictTags:
    """Tests for from_dict handling of tags field."""

    def test_from_dict_accepts_list_format_tags(self) -> None:
        """from_dict should accept tags: ['work', 'urgent'] format."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["work", "urgent"]})
        assert todo.tags == ("work", "urgent")

    def test_from_dict_accepts_tuple_format_tags(self) -> None:
        """from_dict should accept tags as tuple format."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": ("work", "urgent")})
        assert todo.tags == ("work", "urgent")

    def test_from_dict_handles_missing_tags(self) -> None:
        """from_dict should default to empty tuple if tags not provided."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.tags == ()

    def test_from_dict_handles_empty_tags(self) -> None:
        """from_dict should handle empty tags list."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": []})
        assert todo.tags == ()


class TestCliTagFilter:
    """Tests for CLI --tag filtering."""

    def test_cli_list_with_tag_filter(self, tmp_path, capsys) -> None:
        """CLI list --tag work should only show todos containing 'work' tag."""
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        # Add todos with different tags
        todos = [
            Todo(id=1, text="Work task", tags=("work", "urgent")),
            Todo(id=2, text="Personal task", tags=("personal",)),
            Todo(id=3, text="Work task 2", tags=("work", "project-a")),
            Todo(id=4, text="Untagged task"),
        ]
        storage.save(todos)

        # Run CLI with --tag filter
        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "list", "--tag", "work"])
        result = run_command(args)

        assert result == 0
        captured = capsys.readouterr()
        # Should show work tasks
        assert "Work task" in captured.out
        assert "Work task 2" in captured.out
        # Should NOT show personal or untagged tasks
        assert "Personal task" not in captured.out
        assert "Untagged task" not in captured.out

    def test_cli_list_tag_filter_no_matches(self, tmp_path, capsys) -> None:
        """CLI list --tag with no matches should show empty list."""
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="Work task", tags=("work",)),
            Todo(id=2, text="Personal task", tags=("personal",)),
        ]
        storage.save(todos)

        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "list", "--tag", "nonexistent"])
        result = run_command(args)

        assert result == 0
        captured = capsys.readouterr()
        # Should show no todos (empty output or just headers)
        assert "Work task" not in captured.out
        assert "Personal task" not in captured.out

    def test_cli_list_tag_filter_combines_with_pending(self, tmp_path, capsys) -> None:
        """--tag should combine with --pending filter."""
        db = tmp_path / "test.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="Done work task", tags=("work",), done=True),
            Todo(id=2, text="Pending work task", tags=("work",), done=False),
            Todo(id=3, text="Pending personal task", tags=("personal",)),
        ]
        storage.save(todos)

        parser = build_parser()
        args = parser.parse_args(["--db", str(db), "list", "--pending", "--tag", "work"])
        result = run_command(args)

        assert result == 0
        captured = capsys.readouterr()
        # Should only show pending work task
        assert "Pending work task" in captured.out
        assert "Done work task" not in captured.out
        assert "Personal task" not in captured.out
