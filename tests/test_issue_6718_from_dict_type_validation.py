"""Tests for issue #6718: Todo.from_dict type validation.

Bug: Todo.from_dict(None) raises TypeError instead of ValueError with clear message.

This test suite verifies that Todo.from_dict properly validates input types
and raises ValueError (not TypeError) with a clear message when passed
non-dict arguments like None, lists, or strings.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_none_raises_value_error() -> None:
    """Todo.from_dict(None) should raise ValueError, not TypeError."""
    with pytest.raises(ValueError, match="dict"):
        Todo.from_dict(None)


def test_from_dict_list_raises_value_error() -> None:
    """Todo.from_dict([]) should raise ValueError with message containing 'dict'."""
    with pytest.raises(ValueError, match="dict"):
        Todo.from_dict([1, 2])


def test_from_dict_string_raises_value_error() -> None:
    """Todo.from_dict('string') should raise ValueError with message containing 'dict'."""
    with pytest.raises(ValueError, match="dict"):
        Todo.from_dict("string")


def test_from_dict_integer_raises_value_error() -> None:
    """Todo.from_dict(123) should raise ValueError with message containing 'dict'."""
    with pytest.raises(ValueError, match="dict"):
        Todo.from_dict(123)


def test_from_dict_valid_dict_still_works() -> None:
    """Valid dict should still work correctly after type validation."""
    todo = Todo.from_dict({"id": 1, "text": "test task"})
    assert todo.id == 1
    assert todo.text == "test task"
    assert todo.done is False


def test_from_dict_valid_dict_with_all_fields() -> None:
    """Valid dict with all fields should work correctly."""
    todo = Todo.from_dict({
        "id": 42,
        "text": "complete task",
        "done": True,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-02T00:00:00+00:00",
    })
    assert todo.id == 42
    assert todo.text == "complete task"
    assert todo.done is True
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
    assert todo.updated_at == "2024-01-02T00:00:00+00:00"
