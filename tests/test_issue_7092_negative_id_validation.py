"""Tests for issue #7092: from_dict should reject negative IDs.

Bug: Todo.from_dict() accepts negative IDs without validation, which can cause
logic errors in storage.next_id() which uses max() to calculate next ID.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_negative_id() -> None:
    """Bug #7092: Todo.from_dict() should reject negative IDs."""
    with pytest.raises(ValueError, match="non-negative integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_from_dict_rejects_negative_id_with_large_value() -> None:
    """Bug #7092: Todo.from_dict() should reject large negative IDs."""
    with pytest.raises(ValueError, match="non-negative integer"):
        Todo.from_dict({"id": -999, "text": "test"})


def test_from_dict_accepts_zero_id() -> None:
    """Bug #7092: Todo.from_dict() should accept id=0 as valid."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0
    assert todo.text == "test"


def test_from_dict_accepts_positive_id() -> None:
    """Bug #7092: Todo.from_dict() should accept positive IDs as before."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"


def test_from_dict_accepts_large_positive_id() -> None:
    """Bug #7092: Todo.from_dict() should accept large positive IDs."""
    todo = Todo.from_dict({"id": 999999, "text": "test"})
    assert todo.id == 999999
    assert todo.text == "test"
