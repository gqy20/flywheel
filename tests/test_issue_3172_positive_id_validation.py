"""Tests for positive ID validation (Issue #3172).

These tests verify that Todo.from_dict rejects non-positive id values
(0, negative) with a clear error message, ensuring data integrity.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 as invalid (ids must be positive)."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative ids as invalid."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative ids as invalid."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
        Todo.from_dict({"id": -999, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept id=1 as valid positive id."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"


def test_todo_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive ids."""
    todo = Todo.from_dict({"id": 999999, "text": "task"})
    assert todo.id == 999999
