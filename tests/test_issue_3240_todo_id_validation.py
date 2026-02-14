"""Tests for Todo.from_dict id validation (Issue #3240).

These tests verify that Todo.from_dict rejects invalid id values:
1. id <= 0 should be rejected (must be positive)
2. This aligns with storage.next_id() which always starts at 1
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 since system-generated ids start at 1."""
    with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*must be.*greater"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*must be.*greater"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept valid positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    todo2 = Todo.from_dict({"id": 100, "text": "another task"})
    assert todo2.id == 100
