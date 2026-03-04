"""Tests for Todo tags/categories field (Issue #7193).

These tests verify that:
1. Todo has tags field as immutable tuple
2. Empty tuple is default, tags are preserved via serialization
3. Tags are normalized (stripped, lowercase) on creation
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_tags_field() -> None:
    """Todo should have a tags field with default empty tuple."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "tags")
    assert todo.tags == ()


def test_todo_tags_stored_as_tuple() -> None:
    """Tags should be stored as immutable tuple."""
    todo = Todo(id=1, text="test task", tags=["work", "urgent"])
    assert isinstance(todo.tags, tuple)
    assert todo.tags == ("work", "urgent")


def test_todo_tags_to_dict_includes_tags() -> None:
    """to_dict should include tags as a list for JSON serialization."""
    todo = Todo(id=1, text="test task", tags=["work", "urgent"])
    data = todo.to_dict()

    assert "tags" in data
    assert data["tags"] == ("work", "urgent")  # tuple preserved internally


def test_todo_tags_from_dict_with_tags() -> None:
    """from_dict should load tags from dict data."""
    data = {"id": 1, "text": "test task", "tags": ["personal", "home"]}
    todo = Todo.from_dict(data)

    assert todo.tags == ("personal", "home")


def test_todo_tags_from_dict_without_tags() -> None:
    """from_dict should default to empty tuple if tags not present."""
    data = {"id": 1, "text": "test task"}
    todo = Todo.from_dict(data)

    assert todo.tags == ()


def test_todo_tags_roundtrip_preserves_tags() -> None:
    """to_dict/from_dict round-trip should preserve tags."""
    original = Todo(id=1, text="test task", tags=["work", "urgent"])
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.tags == ("work", "urgent")


def test_todo_tags_normalized_lowercase() -> None:
    """Tags should be normalized to lowercase."""
    todo = Todo(id=1, text="test task", tags=["WORK", "Urgent"])
    assert todo.tags == ("work", "urgent")


def test_todo_tags_normalized_stripped() -> None:
    """Tags should have whitespace stripped."""
    todo = Todo(id=1, text="test task", tags=["  work  ", " urgent "])
    assert todo.tags == ("work", "urgent")


def test_todo_tags_empty_after_normalization_removed() -> None:
    """Tags that become empty after stripping should be removed."""
    todo = Todo(id=1, text="test task", tags=["work", "   ", "urgent"])
    assert todo.tags == ("work", "urgent")


def test_todo_tags_accepts_tuple_input() -> None:
    """Tags should accept tuple input directly."""
    todo = Todo(id=1, text="test task", tags=("work", "urgent"))
    assert todo.tags == ("work", "urgent")


def test_todo_tags_accepts_list_input() -> None:
    """Tags should accept list input and convert to tuple."""
    todo = Todo(id=1, text="test task", tags=["work", "urgent"])
    assert todo.tags == ("work", "urgent")
    assert isinstance(todo.tags, tuple)
