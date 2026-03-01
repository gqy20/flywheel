"""Tests for Issue #6576 - Todo.from_dict should reject bool as ID.

In Python, bool is a subclass of int, so int(True) == 1 and int(False) == 0.
This means Todo.from_dict({'id': True, ...}) would silently convert True to 1,
which is confusing and error-prone.

This test file ensures that boolean values are explicitly rejected as IDs.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_bool_true_as_id() -> None:
    """Todo.from_dict should reject True as an ID value."""
    with pytest.raises(ValueError, match=r"'id'.*bool|boolean.*'id'|'id'.*integer"):
        Todo.from_dict({"id": True, "text": "test"})


def test_todo_from_dict_rejects_bool_false_as_id() -> None:
    """Todo.from_dict should reject False as an ID value."""
    with pytest.raises(ValueError, match=r"'id'.*bool|boolean.*'id'|'id'.*integer"):
        Todo.from_dict({"id": False, "text": "test"})


def test_todo_from_dict_accepts_integer_one_as_id() -> None:
    """Todo.from_dict should accept integer 1 as a valid ID."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1


def test_todo_from_dict_accepts_integer_zero_as_id() -> None:
    """Todo.from_dict should accept integer 0 as a valid ID."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0
