"""Test for issue #4397: Todo.from_dict rejects zero as valid id.

Bug: Todo.from_dict accepts zero as valid id but next_id starts from 1.
Fix: Validate id >= 1 to match next_id() behavior.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_zero_id() -> None:
    """Issue #4397: Todo.from_dict should reject id=0.

    next_id() returns minimum value of 1, so from_dict should be consistent
    and reject id=0 to maintain invariant that all todo ids are >= 1.
    """
    with pytest.raises(ValueError, match="'id' must be a positive integer"):
        Todo.from_dict({"id": 0, "text": "test todo"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Issue #4397: Todo.from_dict should reject negative ids.

    Negative ids are never produced by next_id() and should be rejected.
    """
    with pytest.raises(ValueError, match="'id' must be a positive integer"):
        Todo.from_dict({"id": -1, "text": "test todo"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Issue #4397: Todo.from_dict should accept positive ids (>= 1)."""
    todo = Todo.from_dict({"id": 1, "text": "test todo"})
    assert todo.id == 1
    assert todo.text == "test todo"


def test_todo_from_dict_accepts_large_positive_id() -> None:
    """Issue #4397: Todo.from_dict should accept large positive ids."""
    todo = Todo.from_dict({"id": 1000, "text": "test todo"})
    assert todo.id == 1000
