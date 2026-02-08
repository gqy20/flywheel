"""Tests for Issue #2345 - explicit int-to-bool conversion for 'done' field.

These tests verify that:
1. Int 0 explicitly converts to False
2. Int 1 explicitly converts to True
3. Ints other than 0/1 raise ValueError
4. Bool True/False are still accepted

The fix makes the conversion intent explicit rather than relying on bool().
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_int_0_converts_to_false() -> None:
    """Todo.from_dict should convert int 0 to boolean False for 'done' field."""
    todo = Todo.from_dict({"id": 1, "text": "task", "done": 0})
    assert todo.done is False
    assert isinstance(todo.done, bool)


def test_todo_from_dict_int_1_converts_to_true() -> None:
    """Todo.from_dict should convert int 1 to boolean True for 'done' field."""
    todo = Todo.from_dict({"id": 1, "text": "task", "done": 1})
    assert todo.done is True
    assert isinstance(todo.done, bool)


def test_todo_from_dict_int_2_raises_value_error() -> None:
    """Todo.from_dict should reject int 2 for 'done' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'done'"):
        Todo.from_dict({"id": 1, "text": "task", "done": 2})


def test_todo_from_dict_int_negative_raises_value_error() -> None:
    """Todo.from_dict should reject negative integers for 'done' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'done'"):
        Todo.from_dict({"id": 1, "text": "task", "done": -1})


def test_todo_from_dict_bool_true_accepted() -> None:
    """Todo.from_dict should accept bool True for 'done' field."""
    todo = Todo.from_dict({"id": 1, "text": "task", "done": True})
    assert todo.done is True
    assert isinstance(todo.done, bool)


def test_todo_from_dict_bool_false_accepted() -> None:
    """Todo.from_dict should accept bool False for 'done' field."""
    todo = Todo.from_dict({"id": 1, "text": "task", "done": False})
    assert todo.done is False
    assert isinstance(todo.done, bool)


def test_todo_from_dict_default_done_is_false() -> None:
    """Todo.from_dict should default 'done' to False when not provided."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.done is False
