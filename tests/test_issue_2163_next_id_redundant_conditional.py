"""Tests for next_id() redundant conditional logic (Issue #2163).

These tests verify that:
1. next_id([]) returns 1 for empty list (new database case)
2. next_id() correctly handles sequential IDs
3. next_id() correctly handles gaps in IDs
4. Code simplification doesn't break existing behavior
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list() -> None:
    """Bug #2163: next_id([]) should return 1 for empty list.

    This is the critical test case for new databases or when all todos are deleted.
    The simplified code should handle this correctly without the redundant conditional.
    """
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected 1 for empty list, got {result}"


def test_next_id_returns_2_for_single_todo() -> None:
    """Bug #2163: next_id([Todo(id=1)]) should return 2."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first")]
    result = storage.next_id(todos)
    assert result == 2, f"Expected 2 for single todo with id=1, got {result}"


def test_next_id_handles_gaps_in_ids() -> None:
    """Bug #2163: next_id() should handle gaps (e.g., after deletions).

    Example: If todos have ids [1, 3], next_id should return 4 (max + 1),
    not 2 (which would cause a duplicate id=1 conflict).
    """
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=3, text="third")]
    result = storage.next_id(todos)
    assert result == 4, f"Expected 4 for todos with ids [1, 3], got {result}"


def test_next_id_returns_max_plus_one() -> None:
    """Bug #2163: next_id() should always return max(existing_ids) + 1."""
    storage = TodoStorage()

    # Test with various ID sequences
    test_cases = [
        ([Todo(id=1, text="a")], 2),
        ([Todo(id=1, text="a"), Todo(id=2, text="b")], 3),
        ([Todo(id=5, text="gap")], 6),
        ([Todo(id=10, text="x"), Todo(id=20, text="y"), Todo(id=15, text="z")], 21),
    ]

    for todos, expected in test_cases:
        result = storage.next_id(todos)
        assert result == expected, f"Expected {expected} for {[(t.id, t.text) for t in todos]}, got {result}"
