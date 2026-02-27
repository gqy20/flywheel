"""Tests for float ID validation in from_dict (Issue #6107).

These tests verify that:
1. Non-integer float IDs (like 1.5) are rejected with a clear error
2. Integer-valued float IDs (like 1.0) are accepted
3. Regular integer IDs continue to work as expected

This prevents silent data truncation where int(1.5) -> 1 would lose precision.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_non_integer_float_id() -> None:
    """Todo.from_dict should reject non-integer float IDs like 1.5 to prevent truncation."""
    with pytest.raises(ValueError, match=r"integer|float|truncat"):
        Todo.from_dict({"id": 1.5, "text": "task"})


def test_todo_from_dict_rejects_non_integer_float_id_2_7() -> None:
    """Todo.from_dict should reject other non-integer floats like 2.7."""
    with pytest.raises(ValueError, match=r"integer|float|truncat"):
        Todo.from_dict({"id": 2.7, "text": "another task"})


def test_todo_from_dict_accepts_integer_valued_float_id() -> None:
    """Todo.from_dict should accept float IDs that are whole numbers like 1.0."""
    # This is acceptable because int(1.0) == 1 with no data loss
    todo = Todo.from_dict({"id": 1.0, "text": "task"})
    assert todo.id == 1


def test_todo_from_dict_accepts_integer_valued_float_id_large() -> None:
    """Todo.from_dict should accept large integer-valued float IDs like 100.0."""
    todo = Todo.from_dict({"id": 100.0, "text": "task"})
    assert todo.id == 100


def test_todo_from_dict_accepts_integer_id() -> None:
    """Todo.from_dict should continue to accept regular integer IDs."""
    todo = Todo.from_dict({"id": 42, "text": "task"})
    assert todo.id == 42


def test_todo_from_dict_rejects_negative_non_integer_float_id() -> None:
    """Todo.from_dict should reject negative non-integer floats like -1.5."""
    with pytest.raises(ValueError, match=r"integer|float|truncat"):
        Todo.from_dict({"id": -1.5, "text": "task"})
