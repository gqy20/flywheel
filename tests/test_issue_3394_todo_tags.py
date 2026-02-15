"""Tests for Todo tags/category field support (Issue #3394).

These tests verify that:
1. Todo supports optional tags list field
2. from_dict/to_dict correctly serialize/deserialize tags
3. Empty list [] vs None semantics are correctly distinguished
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_with_tags_creation() -> None:
    """Todo(id=1, text='a', tags=['work']) should create successfully."""
    todo = Todo(id=1, text="a", tags=["work"])
    assert todo.tags == ["work"]


def test_todo_tags_default_to_none() -> None:
    """tags should default to None when not provided."""
    todo = Todo(id=1, text="test")
    assert todo.tags is None


def test_todo_with_empty_tags_list() -> None:
    """Todo should support empty tags list []."""
    todo = Todo(id=1, text="test", tags=[])
    assert todo.tags == []


def test_todo_to_dict_includes_tags() -> None:
    """to_dict() should include tags field."""
    todo = Todo(id=1, text="test", tags=["work", "personal"])
    data = todo.to_dict()
    assert "tags" in data
    assert data["tags"] == ["work", "personal"]


def test_todo_to_dict_includes_none_tags() -> None:
    """to_dict() should include tags=None when tags is None."""
    todo = Todo(id=1, text="test")
    data = todo.to_dict()
    assert "tags" in data
    assert data["tags"] is None


def test_todo_to_dict_includes_empty_tags() -> None:
    """to_dict() should include tags=[] when tags is empty list."""
    todo = Todo(id=1, text="test", tags=[])
    data = todo.to_dict()
    assert "tags" in data
    assert data["tags"] == []


def test_todo_from_dict_with_tags() -> None:
    """from_dict() should correctly deserialize tags."""
    data = {"id": 1, "text": "test", "tags": ["work"]}
    todo = Todo.from_dict(data)
    assert todo.tags == ["work"]


def test_todo_from_dict_without_tags() -> None:
    """from_dict() should set tags to None when not in data."""
    data = {"id": 1, "text": "test"}
    todo = Todo.from_dict(data)
    assert todo.tags is None


def test_todo_from_dict_with_empty_tags() -> None:
    """from_dict() should correctly deserialize empty tags list."""
    data = {"id": 1, "text": "test", "tags": []}
    todo = Todo.from_dict(data)
    assert todo.tags == []


def test_todo_roundtrip_with_tags() -> None:
    """Tags should survive to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="test", tags=["work", "personal"])
    roundtrip = Todo.from_dict(original.to_dict())
    assert roundtrip.tags == ["work", "personal"]


def test_todo_roundtrip_with_none_tags() -> None:
    """None tags should survive to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="test")
    roundtrip = Todo.from_dict(original.to_dict())
    assert roundtrip.tags is None


def test_todo_roundtrip_with_empty_tags() -> None:
    """Empty tags list should survive to_dict/from_dict roundtrip."""
    original = Todo(id=1, text="test", tags=[])
    roundtrip = Todo.from_dict(original.to_dict())
    assert roundtrip.tags == []
