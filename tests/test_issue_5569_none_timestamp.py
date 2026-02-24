"""Tests for None timestamp handling in Todo.from_dict (Issue #5569).

These tests verify that:
1. Todo.from_dict with explicit None timestamp results in empty string (not generated timestamp)
2. Todo.from_dict with empty string timestamp preserves the empty string
3. Todo.from_dict with missing timestamp field results in empty string (not generated timestamp)
4. Todo.from_dict with valid ISO timestamp preserves the timestamp
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_explicit_none_created_at_results_in_empty_string() -> None:
    """Todo.from_dict with explicit None created_at should result in empty string."""
    todo = Todo.from_dict({"id": 1, "text": "a", "created_at": None})
    assert todo.created_at == ""


def test_from_dict_explicit_none_updated_at_results_in_empty_string() -> None:
    """Todo.from_dict with explicit None updated_at should result in empty string."""
    todo = Todo.from_dict({"id": 1, "text": "a", "updated_at": None})
    assert todo.updated_at == ""


def test_from_dict_empty_string_timestamp_preserved() -> None:
    """Todo.from_dict with empty string timestamp should preserve empty string."""
    todo = Todo.from_dict({"id": 1, "text": "a", "created_at": ""})
    assert todo.created_at == ""


def test_from_dict_missing_timestamp_results_in_empty_string() -> None:
    """Todo.from_dict without timestamp field should result in empty string."""
    todo = Todo.from_dict({"id": 1, "text": "a"})
    assert todo.created_at == ""


def test_from_dict_valid_timestamp_preserved() -> None:
    """Todo.from_dict with valid ISO timestamp should preserve the timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "a", "created_at": "2024-01-01T00:00:00+00:00"})
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
