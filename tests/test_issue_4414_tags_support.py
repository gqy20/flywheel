"""Tests for Todo tags/category field support (Issue #4414).

These tests verify that:
1. Todo supports optional tags field (default empty tuple)
2. from_dict accepts list or tuple format for tags
3. CLI list supports --tag filter parameter
"""

from __future__ import annotations

from flywheel.cli import TodoApp
from flywheel.todo import Todo


class TestTodoTagsField:
    """Tests for Todo.tags field."""

    def test_todo_with_tags_creates_successfully(self) -> None:
        """Todo with tags should create normally."""
        todo = Todo(id=1, text="buy milk", tags=("work", "urgent"))
        assert todo.tags == ("work", "urgent")

    def test_todo_without_tags_defaults_to_empty_tuple(self) -> None:
        """Todo without tags should have empty tuple as default."""
        todo = Todo(id=1, text="buy milk")
        assert todo.tags == ()

    def test_todo_tags_is_tuple(self) -> None:
        """Tags field should always be a tuple."""
        todo = Todo(id=1, text="task", tags=("work",))
        assert isinstance(todo.tags, tuple)


class TestTodoFromDictTags:
    """Tests for Todo.from_dict() handling of tags."""

    def test_from_dict_accepts_list_format_tags(self) -> None:
        """from_dict should accept tags as a list."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "tags": ["work", "urgent"],
        })
        assert todo.tags == ("work", "urgent")
        assert isinstance(todo.tags, tuple)

    def test_from_dict_accepts_tuple_format_tags(self) -> None:
        """from_dict should accept tags as a tuple."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "tags": ("work", "urgent"),
        })
        assert todo.tags == ("work", "urgent")

    def test_from_dict_missing_tags_defaults_to_empty(self) -> None:
        """from_dict should default to empty tuple if tags missing."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.tags == ()

    def test_from_dict_empty_tags_list(self) -> None:
        """from_dict should handle empty tags list."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": []})
        assert todo.tags == ()


class TestTodoToDictTags:
    """Tests for Todo.to_dict() serialization of tags."""

    def test_to_dict_serializes_tags_as_list(self) -> None:
        """to_dict should serialize tags as a list for JSON compatibility."""
        todo = Todo(id=1, text="task", tags=("work", "urgent"))
        data = todo.to_dict()
        assert data["tags"] == ["work", "urgent"]
        assert isinstance(data["tags"], list)

    def test_to_dict_empty_tags(self) -> None:
        """to_dict should handle empty tags."""
        todo = Todo(id=1, text="task", tags=())
        data = todo.to_dict()
        assert data["tags"] == []


class TestCLITagFilter:
    """Tests for CLI --tag filter functionality."""

    def test_list_filter_by_tag(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """CLI list --tag should filter todos by tag."""
        db_path = str(tmp_path / ".todo.json")
        app = TodoApp(db_path=db_path)

        # Add todos with different tags
        todo1 = Todo(id=1, text="work task", tags=("work",))
        todo2 = Todo(id=2, text="personal task", tags=("personal",))
        todo3 = Todo(id=3, text="urgent work", tags=("work", "urgent"))

        app._save([todo1, todo2, todo3])

        # Filter by 'work' tag
        filtered = app.list(tag="work")
        assert len(filtered) == 2
        assert all("work" in t.tags for t in filtered)

    def test_list_filter_by_tag_no_match(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """CLI list --tag should return empty list when no match."""
        db_path = str(tmp_path / ".todo.json")
        app = TodoApp(db_path=db_path)

        todo1 = Todo(id=1, text="work task", tags=("work",))
        app._save([todo1])

        filtered = app.list(tag="personal")
        assert filtered == []

    def test_list_without_tag_filter_returns_all(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """CLI list without --tag should return all todos."""
        db_path = str(tmp_path / ".todo.json")
        app = TodoApp(db_path=db_path)

        todo1 = Todo(id=1, text="work task", tags=("work",))
        todo2 = Todo(id=2, text="no tags task", tags=())
        app._save([todo1, todo2])

        all_todos = app.list()
        assert len(all_todos) == 2


class TestAddTodoWithTags:
    """Tests for adding todos with tags via TodoApp."""

    def test_add_todo_with_tag(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """TodoApp.add should support adding todo with tags."""
        db_path = str(tmp_path / ".todo.json")
        app = TodoApp(db_path=db_path)

        todo = app.add("work task", tags=("work",))
        assert todo.tags == ("work",)

        # Verify persistence
        loaded = app._load()
        assert len(loaded) == 1
        assert loaded[0].tags == ("work",)

    def test_add_todo_without_tags(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """TodoApp.add without tags should default to empty tuple."""
        db_path = str(tmp_path / ".todo.json")
        app = TodoApp(db_path=db_path)

        todo = app.add("simple task")
        assert todo.tags == ()


class TestCLIListTagArgument:
    """Tests for CLI list --tag argument."""

    def test_cli_list_accepts_tag_argument(self, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
        """CLI list command should accept --tag argument and filter correctly."""
        from flywheel.cli import main

        db_path = str(tmp_path / ".todo.json")
        app = TodoApp(db_path=db_path)

        # Add todos with different tags
        app.add("work task", tags=("work",))
        app.add("personal task", tags=("personal",))
        app.add("urgent work", tags=("work", "urgent"))

        # Run CLI with --tag work
        exit_code = main(["--db", db_path, "list", "--tag", "work"])
        assert exit_code == 0

        # Check output only contains work-tagged todos
        captured = capsys.readouterr()
        assert "work task" in captured.out
        assert "urgent work" in captured.out
        assert "personal task" not in captured.out

    def test_cli_list_tag_no_match_returns_empty(self, tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
        """CLI list --tag with no matches should show no todos."""
        from flywheel.cli import main

        db_path = str(tmp_path / ".todo.json")
        app = TodoApp(db_path=db_path)
        app.add("work task", tags=("work",))

        exit_code = main(["--db", db_path, "list", "--tag", "personal"])
        assert exit_code == 0

        captured = capsys.readouterr()
        # Should have no todo entries (just empty list output)
        assert "work task" not in captured.out
