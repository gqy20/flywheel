"""Tests for Todo ID validation (Issue #6659).

These tests verify that:
1. Todo.from_dict rejects negative IDs with ValueError
2. Todo.from_dict rejects zero ID with ValueError
3. Todo.from_dict accepts positive IDs (id >= 1)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should raise ValueError for negative ID."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": -1, "text": "test"})
    assert "positive" in str(exc_info.value).lower()


def test_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should raise ValueError for zero ID."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 0, "text": "test"})
    assert "positive" in str(exc_info.value).lower()


def test_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive ID (id >= 1)."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"


def test_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive IDs."""
    todo = Todo.from_dict({"id": 999999, "text": "test"})
    assert todo.id == 999999
