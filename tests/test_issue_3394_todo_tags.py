"""Tests for Todo tags field (Issue #3394).

These tests verify that:
1. Todo objects support an optional tags field
2. tags defaults to None
3. to_dict and from_dict correctly serialize/deserialize tags
4. Empty list [] and None are semantically distinct
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_with_tags_created_successfully() -> None:
    """Todo should accept a tags parameter with list of strings."""
    todo = Todo(id=1, text="a task", tags=["work", "urgent"])
    assert todo.tags == ["work", "urgent"]


def test_todo_tags_defaults_to_none() -> None:
    """Todo tags should default to None when not provided."""
    todo = Todo(id=1, text="a task")
    assert todo.tags is None


def test_todo_tags_can_be_empty_list() -> None:
    """Todo tags should distinguish between empty list [] and None."""
    todo = Todo(id=1, text="a task", tags=[])
    assert todo.tags == []
    assert todo.tags is not None


def test_todo_to_dict_includes_tags_when_none() -> None:
    """to_dict should include tags field even when None."""
    todo = Todo(id=1, text="a task", tags=None)
    data = todo.to_dict()
    assert "tags" in data
    assert data["tags"] is None


def test_todo_to_dict_includes_tags_with_values() -> None:
    """to_dict should include tags with actual values."""
    todo = Todo(id=1, text="a task", tags=["work", "personal"])
    data = todo.to_dict()
    assert "tags" in data
    assert data["tags"] == ["work", "personal"]


def test_todo_to_dict_includes_empty_tags_list() -> None:
    """to_dict should preserve empty list [] for tags."""
    todo = Todo(id=1, text="a task", tags=[])
    data = todo.to_dict()
    assert data["tags"] == []


def test_todo_from_dict_with_tags() -> None:
    """from_dict should correctly deserialize tags."""
    data = {"id": 1, "text": "a task", "tags": ["work", "urgent"]}
    todo = Todo.from_dict(data)
    assert todo.tags == ["work", "urgent"]


def test_todo_from_dict_without_tags() -> None:
    """from_dict should set tags to None when not in data."""
    data = {"id": 1, "text": "a task"}
    todo = Todo.from_dict(data)
    assert todo.tags is None


def test_todo_from_dict_with_empty_tags_list() -> None:
    """from_dict should preserve empty list [] for tags."""
    data = {"id": 1, "text": "a task", "tags": []}
    todo = Todo.from_dict(data)
    assert todo.tags == []


def test_todo_roundtrip_with_tags() -> None:
    """Full roundtrip: Todo -> to_dict -> from_dict -> Todo should preserve tags."""
    original = Todo(id=1, text="a task", tags=["project-x", "quarterly"])
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.tags == ["project-x", "quarterly"]


def test_todo_roundtrip_preserves_none_tags() -> None:
    """Roundtrip should preserve None tags."""
    original = Todo(id=1, text="a task", tags=None)
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.tags is None


def test_todo_roundtrip_preserves_empty_tags_list() -> None:
    """Roundtrip should preserve empty list [] for tags."""
    original = Todo(id=1, text="a task", tags=[])
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.tags == []
