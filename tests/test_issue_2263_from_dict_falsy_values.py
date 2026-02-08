"""Tests for from_dict handling of falsy values (Issue #2263).

These tests verify that:
1. created_at=0 is preserved as '0' not ''
2. updated_at=0 is preserved as '0' not ''
3. created_at=False is preserved as 'False' not ''
4. updated_at=False is preserved as 'False' not ''
5. Missing created_at defaults to ''
6. Missing updated_at defaults to ''
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_preserves_zero_created_at() -> None:
    """Todo.from_dict should preserve 0 as '0' for created_at field."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": 0})
    assert todo.created_at == "0", (
        f"Expected created_at='0' but got {todo.created_at!r}. "
        "The value 0 should be preserved, not treated as falsy and replaced with ''"
    )


def test_from_dict_preserves_zero_updated_at() -> None:
    """Todo.from_dict should preserve 0 as '0' for updated_at field."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": 0})
    assert todo.updated_at == "0", (
        f"Expected updated_at='0' but got {todo.updated_at!r}. "
        "The value 0 should be preserved, not treated as falsy and replaced with ''"
    )


def test_from_dict_preserves_false_created_at() -> None:
    """Todo.from_dict should preserve False as 'False' for created_at field."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": False})
    assert todo.created_at == "False", (
        f"Expected created_at='False' but got {todo.created_at!r}. "
        "The value False should be preserved, not treated as falsy and replaced with ''"
    )


def test_from_dict_preserves_false_updated_at() -> None:
    """Todo.from_dict should preserve False as 'False' for updated_at field."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": False})
    assert todo.updated_at == "False", (
        f"Expected updated_at='False' but got {todo.updated_at!r}. "
        "The value False should be preserved, not treated as falsy and replaced with ''"
    )


def test_from_dict_default_timestamp_missing_created_at() -> None:
    """Todo.from_dict should auto-fill created_at with timestamp when field is missing."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.created_at != "", (
        f"Expected created_at to be auto-filled with timestamp but got {todo.created_at!r}. "
        "Missing created_at field should trigger __post_init__ to set current timestamp"
    )
    assert todo.created_at.count("-") == 2, (
        f"Expected ISO timestamp format but got {todo.created_at!r}"
    )


def test_from_dict_default_timestamp_missing_updated_at() -> None:
    """Todo.from_dict should auto-fill updated_at with timestamp when field is missing."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.updated_at != "", (
        f"Expected updated_at to be auto-filled with timestamp but got {todo.updated_at!r}. "
        "Missing updated_at field should trigger __post_init__ to set current timestamp"
    )
    assert todo.updated_at.count("-") == 2, (
        f"Expected ISO timestamp format but got {todo.updated_at!r}"
    )


def test_from_dict_preserves_both_zero_values() -> None:
    """Todo.from_dict should preserve 0 for both timestamp fields."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": 0, "updated_at": 0})
    assert todo.created_at == "0"
    assert todo.updated_at == "0"


def test_from_dict_preserves_both_false_values() -> None:
    """Todo.from_dict should preserve False for both timestamp fields."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": False, "updated_at": False})
    assert todo.created_at == "False"
    assert todo.updated_at == "False"
