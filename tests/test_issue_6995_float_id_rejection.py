"""Regression tests for Issue #6995: from_dict should reject float ids.

This test file ensures that float values for 'id' field are rejected
with a clear error message, preventing silent precision loss.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_float_id_with_fractional_part() -> None:
    """Todo.from_dict should reject float ids with fractional parts like 1.5."""
    with pytest.raises(ValueError, match=r"float.*not.*valid|'id'.*float|integer.*not.*float"):
        Todo.from_dict({"id": 1.5, "text": "test task"})


def test_todo_from_dict_rejects_float_id_whole_number() -> None:
    """Todo.from_dict should reject float ids even for whole numbers like 1.0.

    This ensures consistent behavior - if we accept 1.0, we'd have to also
    check for precision loss on other floats, which is error-prone.
    """
    with pytest.raises(ValueError, match=r"float.*not.*valid|'id'.*float|integer.*not.*float"):
        Todo.from_dict({"id": 1.0, "text": "test task"})


def test_todo_from_dict_rejects_large_float_id() -> None:
    """Todo.from_dict should reject large float ids that lose precision when truncated."""
    with pytest.raises(ValueError, match=r"float.*not.*valid|'id'.*float|integer.*not.*float"):
        Todo.from_dict({"id": 12345678901234567890.5, "text": "test task"})


def test_todo_from_dict_accepts_integer_id() -> None:
    """Todo.from_dict should still accept proper integer ids."""
    todo = Todo.from_dict({"id": 42, "text": "test task"})
    assert todo.id == 42
    assert todo.text == "test task"


def test_todo_from_dict_accepts_string_integer_id() -> None:
    """Todo.from_dict should accept string representations of integers for backward compatibility."""
    todo = Todo.from_dict({"id": "123", "text": "test task"})
    assert todo.id == 123
