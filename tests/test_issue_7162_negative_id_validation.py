"""Tests for negative ID validation in from_dict (Issue #7162).

These tests verify that:
1. Todo.from_dict rejects negative IDs with ValueError
2. Todo.from_dict accepts id=0 (non-negative)
3. Todo.from_dict accepts positive IDs
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs with clear error message."""
    with pytest.raises(ValueError, match=r"negative|non-negative|id.*valid"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative IDs as well."""
    with pytest.raises(ValueError, match=r"negative|non-negative|id.*valid"):
        Todo.from_dict({"id": -999, "text": "test"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept id=0 (zero is non-negative)."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1


def test_todo_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive IDs."""
    todo = Todo.from_dict({"id": 999999, "text": "test"})
    assert todo.id == 999999
