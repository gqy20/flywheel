"""Tests for Todo id positive validation (Issue #3172).

These tests verify that Todo.from_dict rejects non-positive id values
(0 and negative integers) with a clear error message.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 with clear error message."""
    with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*> ?0"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*> ?0"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative id values."""
    with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*> ?0"):
        Todo.from_dict({"id": -999, "text": "test"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept valid positive id (baseline)."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive id values."""
    todo = Todo.from_dict({"id": 999999, "text": "test"})
    assert todo.id == 999999
