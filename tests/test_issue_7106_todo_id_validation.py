"""Tests for Todo id validation (Issue #7106).

These tests verify that:
1. Todo.__init__ validates 'id' is non-negative at construction time
2. Negative ids raise ValueError with clear message
3. Zero and positive ids are accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_negative_id() -> None:
    """Todo(id=-1, ...) should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=-1, text="test")
    assert "non-negative" in str(exc_info.value).lower()


def test_todo_accepts_zero_id() -> None:
    """Todo(id=0, ...) should succeed (id=0 is valid)."""
    todo = Todo(id=0, text="test")
    assert todo.id == 0


def test_todo_accepts_positive_id() -> None:
    """Todo(id=1, ...) should succeed."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1


def test_todo_from_dict_rejects_negative_id() -> None:
    """from_dict with negative id should also raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": -5, "text": "test"})
    assert "non-negative" in str(exc_info.value).lower()


def test_todo_from_dict_accepts_zero_id() -> None:
    """from_dict with id=0 should succeed."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0
