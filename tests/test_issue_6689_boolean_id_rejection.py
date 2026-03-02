"""Tests for rejecting boolean values for 'id' field (Issue #6689).

These tests verify that:
1. Todo.from_dict rejects id=True with clear ValueError
2. Todo.from_dict rejects id=False with clear ValueError
3. Todo.from_dict continues to accept integer ids

This addresses the bug where boolean True/False was incorrectly accepted
because bool is a subclass of int in Python, and int(True) returns 1,
int(False) returns 0.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_boolean_true_for_id() -> None:
    """Todo.from_dict should reject boolean True for 'id' field.

    In Python, bool is a subclass of int, so int(True) == 1.
    This is a bug because the 'id' field should only accept integers.
    """
    with pytest.raises(ValueError, match=r"'id'.*boolean|'id'.*integer|boolean.*'id'"):
        Todo.from_dict({"id": True, "text": "test"})


def test_todo_from_dict_rejects_boolean_false_for_id() -> None:
    """Todo.from_dict should reject boolean False for 'id' field.

    In Python, bool is a subclass of int, so int(False) == 0.
    This is a bug because the 'id' field should only accept integers.
    """
    with pytest.raises(ValueError, match=r"'id'.*boolean|'id'.*integer|boolean.*'id'"):
        Todo.from_dict({"id": False, "text": "test"})


def test_todo_from_dict_accepts_integer_id() -> None:
    """Todo.from_dict should continue to accept integer values for 'id' field."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1

    todo_zero = Todo.from_dict({"id": 0, "text": "test"})
    assert todo_zero.id == 0
