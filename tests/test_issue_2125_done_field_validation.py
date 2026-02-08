"""Tests for Todo.from_dict() done field validation (Issue #2125).

These tests verify that:
1. Loading JSON with done=2 (truthy non-boolean int) is rejected
2. Loading JSON with done=-1 (truthy negative int) is rejected
3. Loading JSON with done='false' (truthy string) is rejected
4. Loading JSON with done=true/false (JSON booleans) are accepted
5. Loading JSON with done=1/0 (legacy int values) are accepted for backwards compatibility
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_truthy_non_boolean_int() -> None:
    """Bug #2125: from_dict() should reject integers other than 0 or 1."""
    # done=2 should be rejected (truthy non-boolean int)
    with pytest.raises(ValueError, match="done"):
        Todo.from_dict({"id": 1, "text": "test", "done": 2})

    # done=-1 should be rejected (truthy negative int)
    with pytest.raises(ValueError, match="done"):
        Todo.from_dict({"id": 1, "text": "test", "done": -1})


def test_from_dict_rejects_truthy_string() -> None:
    """Bug #2125: from_dict() should reject string values for done field."""
    # String 'false' should be rejected (bool('false') == True in Python)
    with pytest.raises(ValueError, match="done"):
        Todo.from_dict({"id": 1, "text": "test", "done": "false"})

    # String 'true' should be rejected (bool('true') == True in Python)
    with pytest.raises(ValueError, match="done"):
        Todo.from_dict({"id": 1, "text": "test", "done": "true"})

    # String '' should be rejected
    with pytest.raises(ValueError, match="done"):
        Todo.from_dict({"id": 1, "text": "test", "done": ""})


def test_from_dict_accepts_json_booleans() -> None:
    """Bug #2125: from_dict() should accept JSON boolean values."""
    # done=true (JSON boolean) should work
    todo = Todo.from_dict({"id": 1, "text": "test", "done": True})
    assert todo.done is True

    # done=false (JSON boolean) should work
    todo = Todo.from_dict({"id": 1, "text": "test", "done": False})
    assert todo.done is False


def test_from_dict_accepts_legacy_int_values() -> None:
    """Bug #2125: from_dict() should accept 0 and 1 for backwards compatibility."""
    # done=1 should work (legacy int value)
    todo = Todo.from_dict({"id": 1, "text": "test", "done": 1})
    assert todo.done is True

    # done=0 should work (legacy int value)
    todo = Todo.from_dict({"id": 1, "text": "test", "done": 0})
    assert todo.done is False


def test_from_dict_defaults_done_to_false() -> None:
    """Bug #2125: from_dict() should default done to False when omitted."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.done is False


def test_from_dict_rejects_none_for_done() -> None:
    """Bug #2125: from_dict() should reject None for done field.

    Note: While bool(None) == False in Python, we want strict type checking
    to prevent silent data corruption. If done field is present, it must
    have a valid boolean or integer (0/1) value.
    """
    with pytest.raises(ValueError, match="done"):
        Todo.from_dict({"id": 1, "text": "test", "done": None})
