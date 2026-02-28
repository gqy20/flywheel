"""Tests for float ID truncation fix (Issue #6228).

These tests verify that Todo.from_dict rejects float IDs with non-zero
fractional parts instead of silently truncating them.

Acceptance criteria:
- Todo.from_dict({'id': 1.5, ...}) raises ValueError
- Todo.from_dict({'id': 1.0, ...}) succeeds (integer-representable)
- Todo.from_dict({'id': 1, ...}) succeeds (actual integer)
- Todo.from_dict({'id': '1', ...}) succeeds (string convertible to int)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_positive_float_with_fraction() -> None:
    """Todo.from_dict should reject id=1.5 with ValueError."""
    with pytest.raises(ValueError, match=r"'id'.*integer|integer.*'id'"):
        Todo.from_dict({"id": 1.5, "text": "test"})


def test_todo_from_dict_rejects_larger_float_with_fraction() -> None:
    """Todo.from_dict should reject id=2.7 with ValueError."""
    with pytest.raises(ValueError, match=r"'id'.*integer|integer.*'id'"):
        Todo.from_dict({"id": 2.7, "text": "test"})


def test_todo_from_dict_rejects_negative_float_with_fraction() -> None:
    """Todo.from_dict should reject id=-1.5 with ValueError."""
    with pytest.raises(ValueError, match=r"'id'.*integer|integer.*'id'"):
        Todo.from_dict({"id": -1.5, "text": "test"})


def test_todo_from_dict_accepts_integer_representable_float() -> None:
    """Todo.from_dict should accept id=1.0 and convert to int 1."""
    todo = Todo.from_dict({"id": 1.0, "text": "test"})
    assert todo.id == 1
    assert isinstance(todo.id, int)


def test_todo_from_dict_accepts_negative_integer_representable_float() -> None:
    """Todo.from_dict should accept id=-2.0 and convert to int -2."""
    todo = Todo.from_dict({"id": -2.0, "text": "test"})
    assert todo.id == -2
    assert isinstance(todo.id, int)


def test_todo_from_dict_accepts_actual_integer() -> None:
    """Todo.from_dict should accept actual int id=1."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1


def test_todo_from_dict_accepts_string_integer() -> None:
    """Todo.from_dict should accept string id='1' convertible to int."""
    todo = Todo.from_dict({"id": "1", "text": "test"})
    assert todo.id == 1
