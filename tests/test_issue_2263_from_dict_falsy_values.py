"""Tests for from_dict handling of falsy values (Issue #2263).

These tests verify that:
1. created_at=0 is converted to '0' not '' (the bug)
2. created_at=False is converted to 'False' not '' (the bug)
3. updated_at=0 is converted to '0' not '' (the bug)
4. updated_at=False is converted to 'False' not '' (the bug)
5. Missing keys or None values auto-generate timestamps (existing behavior via __post_init__)
"""

from __future__ import annotations

import re

from flywheel.todo import Todo


def test_from_dict_created_at_zero_preserved() -> None:
    """created_at=0 should be preserved as '0', not converted to empty string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": 0})
    assert todo.created_at == "0"


def test_from_dict_created_at_false_preserved() -> None:
    """created_at=False should be preserved as 'False', not converted to empty string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": False})
    assert todo.created_at == "False"


def test_from_dict_updated_at_zero_preserved() -> None:
    """updated_at=0 should be preserved as '0', not converted to empty string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": 0})
    assert todo.updated_at == "0"


def test_from_dict_updated_at_false_preserved() -> None:
    """updated_at=False should be preserved as 'False', not converted to empty string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": False})
    assert todo.updated_at == "False"


def test_from_dict_missing_created_at_auto_generates_timestamp() -> None:
    """Missing created_at key should auto-generate timestamp (via __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    # Should be an ISO format timestamp, not empty string
    assert todo.created_at != ""
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.created_at)


def test_from_dict_missing_updated_at_auto_generates_timestamp() -> None:
    """Missing updated_at key should auto-generate timestamp (via __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    # Should be an ISO format timestamp, not empty string
    assert todo.updated_at != ""
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.updated_at)


def test_from_dict_created_at_none_auto_generates_timestamp() -> None:
    """created_at=None should auto-generate timestamp (via __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})
    assert todo.created_at != ""
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.created_at)


def test_from_dict_updated_at_none_auto_generates_timestamp() -> None:
    """updated_at=None should auto-generate timestamp (via __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": None})
    assert todo.updated_at != ""
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", todo.updated_at)


def test_from_dict_both_timestamps_zero_preserved() -> None:
    """Both timestamps with value 0 should be preserved."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": 0, "updated_at": 0})
    assert todo.created_at == "0"
    assert todo.updated_at == "0"


def test_from_dict_both_timestamps_false_preserved() -> None:
    """Both timestamps with value False should be preserved."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": False, "updated_at": False})
    assert todo.created_at == "False"
    assert todo.updated_at == "False"
