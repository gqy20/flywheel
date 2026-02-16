"""Tests for from_dict() type checking (Issue #3804).

These tests verify that Todo.from_dict() raises ValueError (not TypeError)
when data is None or non-dict, providing clear error messages.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_raises_valueerror_for_none() -> None:
    """Todo.from_dict should raise ValueError (not TypeError) when data is None."""
    with pytest.raises(ValueError, match=r"dict|dictionary"):
        Todo.from_dict(None)  # type: ignore[arg-type]


def test_todo_from_dict_raises_valueerror_for_list() -> None:
    """Todo.from_dict should raise ValueError (not TypeError) when data is a list."""
    with pytest.raises(ValueError, match=r"dict|dictionary"):
        Todo.from_dict([])  # type: ignore[arg-type]


def test_todo_from_dict_raises_valueerror_for_int() -> None:
    """Todo.from_dict should raise ValueError (not TypeError) when data is an int."""
    with pytest.raises(ValueError, match=r"dict|dictionary"):
        Todo.from_dict(123)  # type: ignore[arg-type]


def test_todo_from_dict_raises_valueerror_for_string() -> None:
    """Todo.from_dict should raise ValueError (not TypeError) when data is a string."""
    with pytest.raises(ValueError, match=r"dict|dictionary"):
        Todo.from_dict("not a dict")  # type: ignore[arg-type]
