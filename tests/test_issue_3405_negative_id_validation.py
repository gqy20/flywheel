"""Regression tests for Issue #3405: Negative id values are accepted without validation.

This test file ensures that negative id values are rejected in Todo.from_dict.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match="id must be non-negative"):
        Todo.from_dict({"id": -1, "text": "Test todo"})


def test_from_dict_rejects_negative_id_large() -> None:
    """Todo.from_dict should reject large negative id values."""
    with pytest.raises(ValueError, match="id must be non-negative"):
        Todo.from_dict({"id": -999, "text": "Test todo"})


def test_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept zero id value (boundary case)."""
    todo = Todo.from_dict({"id": 0, "text": "Test todo"})
    assert todo.id == 0


def test_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "Test todo"})
    assert todo.id == 1
