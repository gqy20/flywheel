"""Tests for Issue #2345 - from_dict bool conversion clarity for 'done' field.

These tests verify that:
1. Int 0 converts to False
2. Int 1 converts to True
3. Ints other than 0/1 raise ValueError
4. Bool True/False are accepted and preserved
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_issue_2345_int_0_converts_to_false() -> None:
    """from_dict({'id': 1, 'text': 't', 'done': 0}) returns Todo with done=False."""
    todo = Todo.from_dict({"id": 1, "text": "test", "done": 0})
    assert todo.done is False


def test_issue_2345_int_1_converts_to_true() -> None:
    """from_dict({'id': 1, 'text': 't', 'done': 1}) returns Todo with done=True."""
    todo = Todo.from_dict({"id": 1, "text": "test", "done": 1})
    assert todo.done is True


def test_issue_2345_int_2_raises_error() -> None:
    """from_dict({'id': 1, 'text': 't', 'done': 2}) raises ValueError."""
    with pytest.raises(ValueError, match=r"Invalid.*'done'"):
        Todo.from_dict({"id": 1, "text": "test", "done": 2})


def test_issue_2345_int_negative_1_raises_error() -> None:
    """from_dict({'id': 1, 'text': 't', 'done': -1}) raises ValueError."""
    with pytest.raises(ValueError, match=r"Invalid.*'done'"):
        Todo.from_dict({"id": 1, "text": "test", "done": -1})


def test_issue_2345_bool_true_preserved() -> None:
    """from_dict with bool True preserves the boolean value."""
    todo = Todo.from_dict({"id": 1, "text": "test", "done": True})
    assert todo.done is True


def test_issue_2345_bool_false_preserved() -> None:
    """from_dict with bool False preserves the boolean value."""
    todo = Todo.from_dict({"id": 1, "text": "test", "done": False})
    assert todo.done is False


def test_issue_2345_string_raises_error() -> None:
    """from_dict should reject string 'true' or 'false' for 'done' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'done'"):
        Todo.from_dict({"id": 1, "text": "test", "done": "true"})
