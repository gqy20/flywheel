"""Tests for timestamp validation in from_dict (Issue #7163).

These tests verify that:
1. from_dict with valid ISO timestamp succeeds
2. from_dict with empty string for timestamps succeeds (default behavior)
3. from_dict with invalid timestamp raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTimestampValidation:
    """Test timestamp validation in Todo.from_dict."""

    def test_from_dict_with_valid_iso_timestamp_succeeds(self) -> None:
        """from_dict should accept valid ISO format timestamps."""
        data = {
            "id": 1,
            "text": "test todo",
            "created_at": "2024-01-15T10:30:00+00:00",
            "updated_at": "2024-01-15T11:30:00+00:00",
        }
        todo = Todo.from_dict(data)
        assert todo.created_at == "2024-01-15T10:30:00+00:00"
        assert todo.updated_at == "2024-01-15T11:30:00+00:00"

    def test_from_dict_with_valid_iso_timestamp_no_timezone_succeeds(self) -> None:
        """from_dict should accept valid ISO format timestamps without timezone."""
        data = {
            "id": 1,
            "text": "test todo",
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T11:30:00",
        }
        todo = Todo.from_dict(data)
        assert todo.created_at == "2024-01-15T10:30:00"
        assert todo.updated_at == "2024-01-15T11:30:00"

    def test_from_dict_with_empty_timestamp_succeeds(self) -> None:
        """from_dict should accept empty string for timestamps (default behavior)."""
        data = {
            "id": 1,
            "text": "test todo",
            "created_at": "",
            "updated_at": "",
        }
        todo = Todo.from_dict(data)
        # Empty strings trigger default behavior in __post_init__
        assert todo.created_at != ""
        assert todo.updated_at != ""

    def test_from_dict_with_no_timestamp_succeeds(self) -> None:
        """from_dict should accept missing timestamp fields (default behavior)."""
        data = {
            "id": 1,
            "text": "test todo",
        }
        todo = Todo.from_dict(data)
        # Missing timestamps trigger default behavior in __post_init__
        assert todo.created_at != ""
        assert todo.updated_at != ""

    def test_from_dict_with_invalid_created_at_raises_value_error(self) -> None:
        """from_dict should reject malformed created_at timestamp."""
        data = {
            "id": 1,
            "text": "test todo",
            "created_at": "not-a-date",
        }
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)
        assert "created_at" in str(exc_info.value)

    def test_from_dict_with_invalid_updated_at_raises_value_error(self) -> None:
        """from_dict should reject malformed updated_at timestamp."""
        data = {
            "id": 1,
            "text": "test todo",
            "updated_at": "invalid-timestamp",
        }
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)
        assert "updated_at" in str(exc_info.value)

    def test_from_dict_with_partial_invalid_timestamp_raises_value_error(
        self,
    ) -> None:
        """from_dict should reject partially malformed timestamps."""
        data = {
            "id": 1,
            "text": "test todo",
            "created_at": "2024-13-45T99:99:99",  # Invalid month/day/time
        }
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)
        assert "created_at" in str(exc_info.value)

    def test_from_dict_with_valid_iso_timestamp_with_milliseconds_succeeds(
        self,
    ) -> None:
        """from_dict should accept valid ISO format timestamps with milliseconds."""
        data = {
            "id": 1,
            "text": "test todo",
            "created_at": "2024-01-15T10:30:00.123456+00:00",
            "updated_at": "2024-01-15T11:30:00.123456+00:00",
        }
        todo = Todo.from_dict(data)
        assert todo.created_at == "2024-01-15T10:30:00.123456+00:00"
        assert todo.updated_at == "2024-01-15T11:30:00.123456+00:00"

    def test_from_dict_with_valid_iso_timestamp_with_z_succeeds(self) -> None:
        """from_dict should accept valid ISO format timestamps with Z timezone."""
        data = {
            "id": 1,
            "text": "test todo",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T11:30:00Z",
        }
        todo = Todo.from_dict(data)
        assert todo.created_at == "2024-01-15T10:30:00Z"
        assert todo.updated_at == "2024-01-15T11:30:00Z"
