"""Tests for float ID rejection in Todo.from_dict (Issue #4314).

These tests verify that Todo.from_dict explicitly rejects float IDs
rather than silently truncating them to int.

For example, Todo.from_dict({'id': 1.5, 'text': 'x'}) should raise
a clear error instead of silently converting 1.5 to 1.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_float_id_with_fractional_part() -> None:
    """Todo.from_dict should reject float IDs like 1.5 instead of truncating to 1."""
    with pytest.raises(ValueError, match=r"float|integer|'id'"):
        Todo.from_dict({"id": 1.5, "text": "task"})


def test_todo_from_dict_rejects_float_id_whole_number() -> None:
    """Todo.from_dict should reject float IDs even if they are whole numbers like 2.0."""
    with pytest.raises(ValueError, match=r"float|integer|'id'"):
        Todo.from_dict({"id": 2.0, "text": "task"})


def test_todo_from_dict_accepts_valid_integer_id() -> None:
    """Todo.from_dict should still accept valid integer IDs."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"
