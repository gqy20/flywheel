"""Tests for negative ID validation (Issue #4060).

These tests verify that Todo.from_dict() rejects negative ID values
while accepting id=0 and positive IDs.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative values for 'id' field."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|'id'.*negative"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept id=0 as valid."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0
    assert todo.text == "test"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should continue to accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"
