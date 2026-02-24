"""Tests for Todo.from_dict timestamp None handling (Issue #5569).

These tests verify that Todo.from_dict properly handles None timestamp values,
ensuring they are not converted to the literal 'None' string.

The key bug is: str(data.get("created_at")) or "" would produce 'None' string
because str(None) = 'None' which is truthy. The correct pattern is:
str(data.get("created_at") or "") which produces empty string.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_from_dict_none_timestamp_not_converted_to_none_string() -> None:
    """Todo.from_dict should NOT convert None timestamps to literal 'None' string.

    This is the core bug: if the code was written as str(data.get("created_at")) or "",
    then str(None) = 'None' which is truthy, so the 'or ""' would never trigger.
    The correct pattern is str(data.get("created_at") or "") which evaluates
    the 'or' first, converting None to "" before str() is called.
    """
    todo = Todo.from_dict({"id": 1, "text": "a", "created_at": None, "updated_at": None})
    # The key assertion: timestamps should NEVER be the literal 'None' string
    assert todo.created_at != "None"
    assert todo.updated_at != "None"


def test_todo_from_dict_missing_timestamp_not_converted_to_none_string() -> None:
    """Todo.from_dict should handle missing timestamps without producing 'None' string."""
    todo = Todo.from_dict({"id": 1, "text": "a"})
    assert todo.created_at != "None"
    assert todo.updated_at != "None"


def test_todo_from_dict_empty_string_timestamp_not_converted_to_none_string() -> None:
    """Todo.from_dict should preserve empty string timestamps without producing 'None' string."""
    todo = Todo.from_dict({"id": 1, "text": "a", "created_at": "", "updated_at": ""})
    assert todo.created_at != "None"
    assert todo.updated_at != "None"


def test_todo_from_dict_valid_timestamp_preserved() -> None:
    """Todo.from_dict should preserve valid ISO timestamp strings."""
    iso_timestamp = "2024-01-15T10:30:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "a", "created_at": iso_timestamp, "updated_at": iso_timestamp})
    assert todo.created_at == iso_timestamp
    assert todo.updated_at == iso_timestamp
