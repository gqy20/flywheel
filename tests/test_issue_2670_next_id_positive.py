"""Regression test for issue #2670: next_id() can return non-positive values if existing todos have negative ids.

The bug occurs when:
- next_id() uses max((todo.id for todo in todos), default=0) + 1
- If todos contain id=-1, max returns -1, so next_id returns 0
- If todos contain id=-5, next_id returns -4

This test verifies next_id() always returns >= 1 for any input list.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestNextIdPositive:
    """Regression tests for issue #2670: ensure next_id() always returns positive values."""

    def test_next_id_with_single_negative_id(self) -> None:
        """Bug #2670: next_id([Todo(id=-1)]) should return >= 1, not 0."""
        storage = TodoStorage()
        todos = [Todo(id=-1, text="negative id")]
        result = storage.next_id(todos)
        assert result >= 1, f"next_id returned {result}, expected >= 1"

    def test_next_id_with_multiple_negative_ids(self) -> None:
        """Bug #2670: next_id([Todo(id=-5), Todo(id=-1)]) should return >= 1, not -4."""
        storage = TodoStorage()
        todos = [Todo(id=-5, text="very negative"), Todo(id=-1, text="less negative")]
        result = storage.next_id(todos)
        assert result >= 1, f"next_id returned {result}, expected >= 1"

    def test_next_id_with_zero_id(self) -> None:
        """Bug #2670: next_id([Todo(id=0)]) should return >= 1, not 1."""
        storage = TodoStorage()
        todos = [Todo(id=0, text="zero id")]
        result = storage.next_id(todos)
        assert result >= 1, f"next_id returned {result}, expected >= 1"

    def test_next_id_with_mixed_negative_and_positive_ids(self) -> None:
        """Bug #2670: next_id should handle mixed positive/negative ids correctly."""
        storage = TodoStorage()
        todos = [
            Todo(id=-10, text="very negative"),
            Todo(id=-1, text="negative"),
            Todo(id=1, text="positive"),
            Todo(id=5, text="more positive"),
        ]
        result = storage.next_id(todos)
        assert result >= 1, f"next_id returned {result}, expected >= 1"

    def test_next_id_with_empty_list(self) -> None:
        """Edge case: next_id([]) should return 1 (default behavior)."""
        storage = TodoStorage()
        todos: list[Todo] = []
        result = storage.next_id(todos)
        assert result == 1, f"next_id returned {result}, expected 1"

    def test_next_id_with_all_positive_ids(self) -> None:
        """Verify normal case still works: next_id should return max + 1."""
        storage = TodoStorage()
        todos = [Todo(id=1, text="first"), Todo(id=2, text="second"), Todo(id=5, text="fifth")]
        result = storage.next_id(todos)
        assert result == 6, f"next_id returned {result}, expected 6"

    def test_next_id_returns_at_least_one_with_negative_max(self) -> None:
        """Bug #2670: Even when max is negative, return at least 1."""
        storage = TodoStorage()
        # Create todos where max id is -100
        todos = [Todo(id=-100, text="large negative"), Todo(id=-200, text="larger negative")]
        result = storage.next_id(todos)
        assert result >= 1, f"next_id returned {result}, expected >= 1"
