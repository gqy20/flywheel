"""Tests for Todo.from_dict handling falsy values (Issue #2263).

These tests verify that from_dict correctly handles falsy values like 0 and False
in created_at and updated_at fields, instead of converting them to empty strings.

Bug: str(data.get("created_at") or "") converts 0 and False to ""
Fix: Use data.get("created_at") if data.get("created_at") is not None else ""

Note: __post_init__ will auto-populate empty timestamps with current time.
So when created_at is missing or None, it gets set to current timestamp.
When created_at is 0 or False, it should be preserved as "0" or "False".
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_created_at_with_zero() -> None:
    """from_dict should preserve 0 as '0' in created_at, not convert to empty string.

    Since '0' is truthy as a string, __post_init__ won't override it.
    """
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": 0})
    assert todo.created_at == "0", f"Expected '0', got {todo.created_at!r}"


def test_from_dict_created_at_with_false() -> None:
    """from_dict should preserve False as 'False' in created_at, not convert to empty string.

    Since 'False' is truthy as a string, __post_init__ won't override it.
    """
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": False})
    assert todo.created_at == "False", f"Expected 'False', got {todo.created_at!r}"


def test_from_dict_created_at_with_empty_string() -> None:
    """from_dict should preserve empty string, but __post_init__ will auto-populate it."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": ""})
    # Empty string gets auto-populated by __post_init__
    assert todo.created_at != "", f"Expected auto-generated timestamp, got {todo.created_at!r}"


def test_from_dict_created_at_missing() -> None:
    """from_dict should use empty string when created_at is missing, then __post_init__ auto-populates."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    # Missing field gets auto-populated by __post_init__
    assert todo.created_at != "", f"Expected auto-generated timestamp, got {todo.created_at!r}"


def test_from_dict_created_at_with_none() -> None:
    """from_dict should convert None to empty string, then __post_init__ auto-populates."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})
    # None becomes "" which gets auto-populated by __post_init__
    assert todo.created_at != "", f"Expected auto-generated timestamp, got {todo.created_at!r}"


def test_from_dict_created_at_with_valid_string() -> None:
    """from_dict should preserve valid timestamp strings."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": "2024-01-01T00:00:00"})
    assert todo.created_at == "2024-01-01T00:00:00"


def test_from_dict_updated_at_with_zero() -> None:
    """from_dict should preserve 0 as '0' in updated_at, not convert to empty string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": 0})
    assert todo.updated_at == "0", f"Expected '0', got {todo.updated_at!r}"


def test_from_dict_updated_at_with_false() -> None:
    """from_dict should preserve False as 'False' in updated_at, not convert to empty string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": False})
    assert todo.updated_at == "False", f"Expected 'False', got {todo.updated_at!r}"


def test_from_dict_both_timestamps_with_falsy_values() -> None:
    """from_dict should handle both timestamps with falsy values correctly."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": 0, "updated_at": False})
    assert todo.created_at == "0", f"Expected '0', got {todo.created_at!r}"
    assert todo.updated_at == "False", f"Expected 'False', got {todo.updated_at!r}"
