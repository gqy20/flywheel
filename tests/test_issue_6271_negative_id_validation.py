"""Tests for negative ID validation (Issue #6271).

These tests verify that:
1. Todo.from_dict rejects negative ID values with clear error message
2. Todo.from_dict accepts ID value of 0 (zero is valid)
3. Todo.from_dict accepts positive ID values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative ID values to prevent next_id() issues."""
    with pytest.raises(ValueError, match=r"non-negative|'id'.*negative"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept ID value of 0."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0
    assert todo.text == "task"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive ID values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"
