"""Tests for Todo.id validation (Issue #3993).

These tests verify that:
1. Todo.from_dict rejects id=0 with ValueError
2. Todo.from_dict rejects negative id values with ValueError
3. Todo.from_dict accepts positive id values
4. Error messages mention 'id' and 'positive'
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 with ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 0, "text": "test"})
    error_msg = str(exc_info.value)
    assert "id" in error_msg.lower()
    assert "positive" in error_msg.lower()


def test_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values with ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": -1, "text": "test"})
    error_msg = str(exc_info.value)
    assert "id" in error_msg.lower()
    assert "positive" in error_msg.lower()


def test_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"


def test_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive id values."""
    todo = Todo.from_dict({"id": 999999, "text": "test"})
    assert todo.id == 999999
