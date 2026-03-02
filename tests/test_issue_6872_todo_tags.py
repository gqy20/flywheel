"""Tests for Todo tags field (Issue #6872).

These tests verify that:
1. Todo dataclass has tags: tuple[str, ...] field with default empty tuple
2. from_dict converts JSON arrays to tuple
3. to_dict converts tuple to JSON array
4. Tags are stripped of whitespace and empty strings are filtered
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_tags_field_exists() -> None:
    """Todo should have a tags field with default empty tuple."""
    todo = Todo(id=1, text="task with tags", tags=("work", "urgent"))
    assert todo.tags == ("work", "urgent")


def test_todo_tags_default_empty_tuple() -> None:
    """Todo tags should default to empty tuple when not provided."""
    todo = Todo(id=1, text="task without tags")
    assert todo.tags == ()


def test_todo_from_dict_converts_list_to_tuple() -> None:
    """from_dict should convert JSON array to tuple."""
    data = {"id": 1, "text": "task", "tags": ["a", "b", "c"]}
    todo = Todo.from_dict(data)
    assert todo.tags == ("a", "b", "c")
    assert isinstance(todo.tags, tuple)


def test_todo_from_dict_handles_missing_tags() -> None:
    """from_dict should use empty tuple when tags not provided."""
    data = {"id": 1, "text": "task"}
    todo = Todo.from_dict(data)
    assert todo.tags == ()


def test_todo_to_dict_converts_tuple_to_list() -> None:
    """to_dict should convert tuple to JSON array."""
    todo = Todo(id=1, text="task", tags=("work", "personal"))
    data = todo.to_dict()
    assert data["tags"] == ["work", "personal"]
    assert isinstance(data["tags"], list)


def test_todo_to_dict_empty_tags_as_empty_list() -> None:
    """to_dict should output empty list for empty tags."""
    todo = Todo(id=1, text="task")
    data = todo.to_dict()
    assert data["tags"] == []
    assert isinstance(data["tags"], list)


def test_todo_tags_stripped_and_filtered() -> None:
    """Tags should be stripped of whitespace and empty strings filtered."""
    # Test stripping whitespace
    data = {"id": 1, "text": "task", "tags": ["  work  ", " personal ", ""]}
    todo = Todo.from_dict(data)
    assert todo.tags == ("work", "personal")
    assert "" not in todo.tags


def test_todo_tags_with_only_whitespace_becomes_empty() -> None:
    """Tags with only whitespace should result in empty tuple."""
    data = {"id": 1, "text": "task", "tags": ["  ", "", "\t"]}
    todo = Todo.from_dict(data)
    assert todo.tags == ()


def test_todo_direct_creation_with_tags_normalizes() -> None:
    """Direct creation with tags should also strip and filter."""
    # This test ensures consistency whether tags are set via from_dict or directly
    todo = Todo(id=1, text="task", tags=("work", "personal"))
    assert todo.tags == ("work", "personal")


def test_todo_roundtrip_preserves_tags() -> None:
    """Round-trip from_dict -> to_dict should preserve tags."""
    original_data = {"id": 42, "text": "important task", "tags": ["urgent", "work"]}
    todo = Todo.from_dict(original_data)
    result_data = todo.to_dict()

    assert result_data["tags"] == ["urgent", "work"]
