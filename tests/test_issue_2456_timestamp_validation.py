"""Regression tests for issue #2456: Todo.from_dict timestamp validation."""

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_int_created_at():
    """from_dict should reject integer created_at values."""
    with pytest.raises(ValueError, match="created_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "created_at": 123})


def test_from_dict_rejects_list_created_at():
    """from_dict should reject list created_at values."""
    with pytest.raises(ValueError, match="created_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "created_at": ["2024-01-01"]})


def test_from_dict_rejects_dict_created_at():
    """from_dict should reject dict created_at values."""
    with pytest.raises(ValueError, match="created_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "created_at": {"date": "2024-01-01"}})


def test_from_dict_rejects_int_updated_at():
    """from_dict should reject integer updated_at values."""
    with pytest.raises(ValueError, match="updated_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "updated_at": 123})


def test_from_dict_rejects_list_updated_at():
    """from_dict should reject list updated_at values."""
    with pytest.raises(ValueError, match="updated_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "updated_at": ["2024-01-01"]})


def test_from_dict_rejects_dict_updated_at():
    """from_dict should reject dict updated_at values."""
    with pytest.raises(ValueError, match="updated_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "updated_at": {"date": "2024-01-01"}})


def test_from_dict_accepts_none_created_at():
    """from_dict should accept None for created_at (will use default)."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})
    assert todo.id == 1
    assert todo.text == "test"
    assert isinstance(todo.created_at, str)
    assert len(todo.created_at) > 0


def test_from_dict_accepts_string_created_at():
    """from_dict should accept valid string created_at values."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": "2024-01-01T00:00:00Z"})
    assert todo.created_at == "2024-01-01T00:00:00Z"


def test_from_dict_accepts_none_updated_at():
    """from_dict should accept None for updated_at (will use default)."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": None})
    assert todo.id == 1
    assert todo.text == "test"
    assert isinstance(todo.updated_at, str)
    assert len(todo.updated_at) > 0


def test_from_dict_accepts_string_updated_at():
    """from_dict should accept valid string updated_at values."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": "2024-01-01T00:00:00Z"})
    assert todo.updated_at == "2024-01-01T00:00:00Z"
