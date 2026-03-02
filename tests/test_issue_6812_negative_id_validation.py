"""Tests for negative ID validation (Issue #6812).

These tests verify that Todo.from_dict rejects negative IDs
which are semantically invalid since IDs should be positive integers.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative values for 'id' field."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|non-negative.*'id'"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative values for 'id' field."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|non-negative.*'id'"):
        Todo.from_dict({"id": -42, "text": "task"})


def test_todo_from_dict_accepts_id_zero() -> None:
    """Todo.from_dict should accept zero as a valid ID.

    Note: While IDs typically start from 1 (per storage.next_id()),
    zero is technically non-negative and could be used for special cases
    like unsaved/temporary items.
    """
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive values for 'id' field."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    todo2 = Todo.from_dict({"id": 42, "text": "another task"})
    assert todo2.id == 42
