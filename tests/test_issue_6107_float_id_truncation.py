"""Tests for float ID truncation protection (Issue #6107).

These tests verify that:
1. Todo.from_dict rejects non-integer float IDs (e.g., 1.5) with ValueError
2. Todo.from_dict accepts integer-valued float IDs (e.g., 1.0)
3. Todo.from_dict continues to accept integer IDs
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_non_integer_float_id() -> None:
    """Todo.from_dict should reject float IDs with non-integer values (e.g., 1.5)."""
    with pytest.raises(ValueError, match=r"'id'.*integer|'id'.*float"):
        Todo.from_dict({"id": 1.5, "text": "test"})


def test_todo_from_dict_accepts_integer_valued_float_id() -> None:
    """Todo.from_dict should accept float IDs that have integer values (e.g., 1.0)."""
    todo = Todo.from_dict({"id": 1.0, "text": "test"})
    assert todo.id == 1


def test_todo_from_dict_accepts_integer_id() -> None:
    """Todo.from_dict should accept integer IDs."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
