"""Tests for Todo ID validation (Issue #6659).

These tests verify that Todo.from_dict rejects negative and zero IDs,
ensuring IDs are positive integers only.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs."""
    with pytest.raises(ValueError, match=r"positive"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero as an ID."""
    with pytest.raises(ValueError, match=r"positive"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
