"""Tests for timestamp validation in from_dict (Issue #4242).

These tests verify that:
1. Todo.from_dict raises ValueError when created_at/updated_at is a non-string type
2. Todo.from_dict accepts valid ISO format timestamp strings
3. Todo.from_dict handles empty/None timestamps gracefully
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTimestampTypeValidation:
    """Tests for validating timestamp types in from_dict."""

    def test_from_dict_rejects_int_created_at(self) -> None:
        """Todo.from_dict should reject integer for 'created_at' field."""
        with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
            Todo.from_dict({"id": 1, "text": "task", "created_at": 1234567890})

    def test_from_dict_rejects_list_created_at(self) -> None:
        """Todo.from_dict should reject list for 'created_at' field."""
        with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
            Todo.from_dict({"id": 1, "text": "task", "created_at": [1, 2, 3]})

    def test_from_dict_rejects_dict_created_at(self) -> None:
        """Todo.from_dict should reject dict for 'created_at' field."""
        with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
            Todo.from_dict({"id": 1, "text": "task", "created_at": {"foo": "bar"}})

    def test_from_dict_rejects_int_updated_at(self) -> None:
        """Todo.from_dict should reject integer for 'updated_at' field."""
        with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
            Todo.from_dict({"id": 1, "text": "task", "updated_at": 1234567890})

    def test_from_dict_rejects_list_updated_at(self) -> None:
        """Todo.from_dict should reject list for 'updated_at' field."""
        with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
            Todo.from_dict({"id": 1, "text": "task", "updated_at": [1, 2, 3]})

    def test_from_dict_rejects_dict_updated_at(self) -> None:
        """Todo.from_dict should reject dict for 'updated_at' field."""
        with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
            Todo.from_dict({"id": 1, "text": "task", "updated_at": {"foo": "bar"}})


class TestTimestampValidStringAcceptance:
    """Tests for accepting valid timestamp strings."""

    def test_from_dict_accepts_valid_iso_created_at(self) -> None:
        """Todo.from_dict should accept valid ISO format string for 'created_at'."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "2026-02-18T12:00:00+00:00"
        })
        assert todo.created_at == "2026-02-18T12:00:00+00:00"

    def test_from_dict_accepts_valid_iso_updated_at(self) -> None:
        """Todo.from_dict should accept valid ISO format string for 'updated_at'."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "updated_at": "2026-02-18T13:00:00+00:00"
        })
        assert todo.updated_at == "2026-02-18T13:00:00+00:00"

    def test_from_dict_accepts_both_valid_timestamps(self) -> None:
        """Todo.from_dict should accept both valid timestamps."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "2026-02-18T12:00:00+00:00",
            "updated_at": "2026-02-18T13:00:00+00:00"
        })
        assert todo.created_at == "2026-02-18T12:00:00+00:00"
        assert todo.updated_at == "2026-02-18T13:00:00+00:00"


class TestTimestampEmptyHandling:
    """Tests for handling empty/None timestamps."""

    def test_from_dict_accepts_missing_created_at(self) -> None:
        """Todo.from_dict should handle missing 'created_at' gracefully."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        # __post_init__ will set created_at to current time
        assert todo.created_at != ""

    def test_from_dict_accepts_missing_updated_at(self) -> None:
        """Todo.from_dict should handle missing 'updated_at' gracefully."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        # __post_init__ will set updated_at to same as created_at
        assert todo.updated_at != ""

    def test_from_dict_accepts_none_created_at(self) -> None:
        """Todo.from_dict should handle None for 'created_at' gracefully."""
        todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})
        # __post_init__ will set created_at to current time
        assert todo.created_at != ""

    def test_from_dict_accepts_empty_string_created_at(self) -> None:
        """Todo.from_dict should accept empty string for 'created_at'."""
        todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})
        # __post_init__ will set created_at to current time since it's empty
        assert todo.created_at != ""

    def test_from_dict_accepts_empty_string_updated_at(self) -> None:
        """Todo.from_dict should accept empty string for 'updated_at'."""
        todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": ""})
        # __post_init__ will set updated_at to created_at since it's empty
        assert todo.updated_at != ""
