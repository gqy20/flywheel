"""Tests for Todo tags field support (Issue #3492)."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoTagsField:
    """Test suite for Todo tags field functionality."""

    def test_todo_has_tags_field_with_default_empty_tuple(self) -> None:
        """Todo dataclass should include tags field with empty tuple as default."""
        todo = Todo(id=1, text="test")
        assert hasattr(todo, "tags")
        assert todo.tags == ()

    def test_todo_accepts_tags_list(self) -> None:
        """Todo should accept list of tags."""
        todo = Todo(id=1, text="x", tags=["work"])
        assert list(todo.tags) == ["work"]

    def test_todo_accepts_tags_tuple(self) -> None:
        """Todo should accept tuple of tags directly."""
        todo = Todo(id=1, text="x", tags=("personal", "urgent"))
        assert todo.tags == ("personal", "urgent")

    def test_from_dict_parses_tags_list(self) -> None:
        """from_dict() should parse tags from list."""
        todo = Todo.from_dict({"id": 1, "text": "x", "tags": ["a", "b"]})
        assert todo.tags == ("a", "b")

    def test_from_dict_tags_default_empty_tuple(self) -> None:
        """from_dict() should return empty tuple when tags not provided."""
        todo = Todo.from_dict({"id": 1, "text": "x"})
        assert todo.tags == ()

    def test_from_dict_tags_empty_list_to_empty_tuple(self) -> None:
        """from_dict() should convert empty list to empty tuple."""
        todo = Todo.from_dict({"id": 1, "text": "x", "tags": []})
        assert todo.tags == ()

    def test_to_dict_includes_tags(self) -> None:
        """to_dict() output should include tags field."""
        todo = Todo(id=1, text="x", tags=["work", "personal"])
        result = todo.to_dict()
        assert "tags" in result
        # Accept list or tuple with same elements
        assert list(result["tags"]) == ["work", "personal"]

    def test_from_dict_rejects_non_string_tags(self) -> None:
        """from_dict() should raise clear error for non-string tag values."""
        with pytest.raises(ValueError, match=r"tags.*string"):
            Todo.from_dict({"id": 1, "text": "x", "tags": [1, 2, 3]})

    def test_from_dict_rejects_non_list_tags(self) -> None:
        """from_dict() should raise clear error for non-list/tuple tags."""
        with pytest.raises(ValueError, match=r"tags.*list"):
            Todo.from_dict({"id": 1, "text": "x", "tags": "work"})

    def test_from_dict_accepts_tuple_tags(self) -> None:
        """from_dict() should accept tuple input for tags."""
        todo = Todo.from_dict({"id": 1, "text": "x", "tags": ("a", "b")})
        assert todo.tags == ("a", "b")

    def test_tags_preserved_in_storage_roundtrip(self, tmp_path) -> None:
        """Tags should survive storage save/load roundtrip."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="x", tags=["work", "urgent"])]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].tags == ("work", "urgent")
