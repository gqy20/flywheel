"""Tests for Todo tags field (Issue #6872)."""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoTagsField:
    """Test tags field support in Todo dataclass."""

    def test_todo_with_tags_creates_successfully(self) -> None:
        """Todo can be created with tags field."""
        todo = Todo(id=1, text="task", tags=("work", "urgent"))
        assert todo.tags == ("work", "urgent")

    def test_todo_tags_defaults_to_empty_tuple(self) -> None:
        """Todo tags should default to an empty tuple."""
        todo = Todo(id=1, text="task")
        assert todo.tags == ()

    def test_from_dict_converts_list_to_tuple(self) -> None:
        """from_dict should convert JSON array to tuple."""
        todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["a", "b"]})
        assert todo.tags == ("a", "b")
        assert isinstance(todo.tags, tuple)

    def test_from_dict_handles_missing_tags(self) -> None:
        """from_dict should handle missing tags field gracefully."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.tags == ()

    def test_from_dict_strips_whitespace_from_tags(self) -> None:
        """Tags should have whitespace stripped."""
        todo = Todo.from_dict(
            {"id": 1, "text": "task", "tags": ["  work  ", "\turgent\t", " personal"]}
        )
        assert todo.tags == ("work", "urgent", "personal")

    def test_from_dict_filters_empty_strings(self) -> None:
        """Empty strings should be filtered from tags."""
        todo = Todo.from_dict(
            {"id": 1, "text": "task", "tags": ["work", "", "  ", "urgent"]}
        )
        assert todo.tags == ("work", "urgent")

    def test_to_dict_outputs_tags_as_list(self) -> None:
        """to_dict should output tags as a JSON array (list)."""
        todo = Todo(id=1, text="task", tags=("work", "urgent"))
        result = todo.to_dict()
        assert result["tags"] == ["work", "urgent"]
        assert isinstance(result["tags"], list)

    def test_to_dict_outputs_empty_list_for_empty_tags(self) -> None:
        """to_dict should output empty list when no tags."""
        todo = Todo(id=1, text="task")
        result = todo.to_dict()
        assert result["tags"] == []
