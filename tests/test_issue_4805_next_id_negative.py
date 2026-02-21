"""Tests for next_id handling of negative IDs (issue #4805).

Regression tests ensuring that next_id always returns a positive ID
even when the storage contains todos with negative IDs.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdWithNegativeIds:
    """Tests for next_id when storage contains negative IDs."""

    def test_next_id_empty_list_returns_1(self) -> None:
        """Test that next_id returns 1 for an empty list."""
        storage = TodoStorage()
        result = storage.next_id([])
        assert result == 1

    def test_next_id_with_positive_ids(self) -> None:
        """Test that next_id returns max_id + 1 for positive IDs."""
        storage = TodoStorage()
        todos = [
            Todo(id=1, text="a"),
            Todo(id=2, text="b"),
            Todo(id=5, text="c"),
        ]
        result = storage.next_id(todos)
        assert result == 6

    def test_next_id_with_negative_ids_returns_positive(self) -> None:
        """Test that next_id returns positive ID when storage has negative IDs.

        When todos contain negative IDs (e.g., -5), next_id should ignore them
        and return a positive ID based on the maximum positive ID or 1.
        """
        storage = TodoStorage()
        # Create todos with negative IDs (which can happen due to data corruption)
        todos = [Todo(id=-5, text="corrupted")]
        result = storage.next_id(todos)
        # Should return 1 (based on max(0, -5) + 1 = 1)
        assert result == 1
        assert result > 0

    def test_next_id_with_mixed_positive_and_negative_ids(self) -> None:
        """Test next_id with both positive and negative IDs.

        The next_id should be based on the maximum positive ID, ignoring negatives.
        """
        storage = TodoStorage()
        todos = [
            Todo(id=-5, text="corrupted1"),
            Todo(id=-1, text="corrupted2"),
            Todo(id=1, text="valid1"),
            Todo(id=10, text="valid2"),
        ]
        result = storage.next_id(todos)
        # Should return 11 (max positive ID 10 + 1), not based on -1 or -5
        assert result == 11
        assert result > 0

    def test_next_id_with_zero_and_negative_ids(self) -> None:
        """Test next_id when IDs include zero and negative values."""
        storage = TodoStorage()
        todos = [
            Todo(id=-3, text="corrupted"),
            Todo(id=0, text="zero_id"),
        ]
        result = storage.next_id(todos)
        # Should return 1 (max(0, 0, -3) + 1 = 1)
        assert result == 1
        assert result > 0

    def test_next_id_all_negative_ids_returns_1(self) -> None:
        """Test that next_id returns 1 when all IDs are negative."""
        storage = TodoStorage()
        todos = [
            Todo(id=-10, text="corrupted1"),
            Todo(id=-5, text="corrupted2"),
            Todo(id=-1, text="corrupted3"),
        ]
        result = storage.next_id(todos)
        # Should return 1 since max of negatives is -1, max(0, -1) = 0, + 1 = 1
        assert result == 1
        assert result > 0
