"""Tests for Todo.from_dict negative id validation (Issue #4076).

These tests verify that:
1. Todo.from_dict rejects negative 'id' values with ValueError
2. Todo.from_dict accepts id=0 (zero is valid)
3. Todo.from_dict continues to accept positive ids
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_negative_id_minus_one() -> None:
    """from_dict should raise ValueError for id=-1."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": -1, "text": "test"})

    assert "non-negative" in str(exc_info.value).lower()


def test_from_dict_rejects_negative_id_minus_hundred() -> None:
    """from_dict should raise ValueError for id=-100."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": -100, "text": "test"})

    assert "non-negative" in str(exc_info.value).lower()


def test_from_dict_accepts_zero_id() -> None:
    """from_dict should accept id=0 (zero is a valid non-negative id)."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0
    assert todo.text == "test"


def test_from_dict_accepts_positive_id() -> None:
    """from_dict should continue to accept positive ids."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"


def test_from_dict_accepts_large_positive_id() -> None:
    """from_dict should accept large positive ids."""
    todo = Todo.from_dict({"id": 999999, "text": "test"})
    assert todo.id == 999999
