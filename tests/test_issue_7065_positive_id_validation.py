"""Tests for Todo.from_dict positive ID validation (Issue #7065).

These tests verify that:
1. Todo.from_dict rejects id=0 with ValueError
2. Todo.from_dict rejects negative IDs with ValueError
3. Todo.from_dict still accepts positive IDs correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 with ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 0, "text": "test"})
    assert "positive integer" in str(exc_info.value).lower()


def test_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs with ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": -1, "text": "test"})
    assert "positive integer" in str(exc_info.value).lower()


def test_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative IDs with ValueError."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": -999, "text": "test"})
    assert "positive integer" in str(exc_info.value).lower()


def test_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs correctly."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"


def test_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive IDs correctly."""
    todo = Todo.from_dict({"id": 999999, "text": "test"})
    assert todo.id == 999999
