"""Tests for Todo tags/category field (Issue #3394).

These tests verify that:
1. Todo supports optional tags list field
2. from_dict/to_dict correctly serialize tags
3. Empty list [] and None are semantically distinct
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_creation_with_tags() -> None:
    """Todo(id=1, text='a', tags=['work']) should create successfully."""
    todo = Todo(id=1, text="a", tags=["work"])
    assert todo.tags == ["work"]


def test_todo_tags_defaults_to_none() -> None:
    """tags should default to None when not provided."""
    todo = Todo(id=1, text="task")
    assert todo.tags is None


def test_todo_tags_empty_list() -> None:
    """Todo should accept an empty tags list []."""
    todo = Todo(id=1, text="task", tags=[])
    assert todo.tags == []


def test_todo_tags_multiple_values() -> None:
    """Todo should support multiple tags."""
    todo = Todo(id=1, text="task", tags=["work", "urgent", "project-x"])
    assert todo.tags == ["work", "urgent", "project-x"]


def test_todo_to_dict_includes_tags() -> None:
    """to_dict should include tags field."""
    todo = Todo(id=1, text="task", tags=["work"])
    data = todo.to_dict()
    assert "tags" in data
    assert data["tags"] == ["work"]


def test_todo_to_dict_tags_none() -> None:
    """to_dict should preserve None for tags."""
    todo = Todo(id=1, text="task")
    data = todo.to_dict()
    assert data["tags"] is None


def test_todo_to_dict_tags_empty_list() -> None:
    """to_dict should preserve empty list [] for tags."""
    todo = Todo(id=1, text="task", tags=[])
    data = todo.to_dict()
    assert data["tags"] == []


def test_todo_from_dict_with_tags() -> None:
    """from_dict should correctly deserialize tags."""
    todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["work", "personal"]})
    assert todo.tags == ["work", "personal"]


def test_todo_from_dict_tags_missing_defaults_to_none() -> None:
    """from_dict should default tags to None when missing."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.tags is None


def test_todo_from_dict_tags_empty_list() -> None:
    """from_dict should correctly deserialize empty tags list."""
    todo = Todo.from_dict({"id": 1, "text": "task", "tags": []})
    assert todo.tags == []


def test_todo_from_dict_tags_none_explicit() -> None:
    """from_dict should handle explicit null tags."""
    todo = Todo.from_dict({"id": 1, "text": "task", "tags": None})
    assert todo.tags is None


def test_todo_roundtrip_with_tags() -> None:
    """Tags should survive to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="task", tags=["work", "urgent"])
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.tags == ["work", "urgent"]


def test_todo_roundtrip_tags_none() -> None:
    """Tags None should survive to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="task")
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.tags is None


def test_todo_roundtrip_tags_empty_list() -> None:
    """Tags empty list should survive to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="task", tags=[])
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.tags == []


def test_todo_from_dict_rejects_invalid_tags_type_string() -> None:
    """from_dict should reject string for tags field."""
    import pytest

    with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list"):
        Todo.from_dict({"id": 1, "text": "task", "tags": "work"})


def test_todo_from_dict_rejects_invalid_tags_type_int() -> None:
    """from_dict should reject int for tags field."""
    import pytest

    with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list"):
        Todo.from_dict({"id": 1, "text": "task", "tags": 123})
