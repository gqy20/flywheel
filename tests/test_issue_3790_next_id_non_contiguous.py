"""Regression test for issue #3790: next_id() with non-contiguous IDs.

Bug: next_id() may return duplicate IDs when todos list has non-contiguous IDs.

The original implementation used max() + 1 which doesn't account for gaps.
If IDs are [1, 3, 5], next_id returned 6 instead of filling the smallest gap (2).

Fix: Use set difference to find the smallest unused positive integer ID.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_fills_gaps_in_non_contiguous_ids() -> None:
    """Issue #3790: next_id() should return smallest unused ID, not max+1."""
    storage = TodoStorage()

    # Create todos with non-contiguous IDs: [1, 3, 5]
    # The smallest unused ID should be 2
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="second"),
        Todo(id=5, text="third"),
    ]

    # Should return 2 (smallest gap), not 6 (max + 1)
    assert storage.next_id(todos) == 2


def test_next_id_fills_first_gap_when_multiple_gaps_exist() -> None:
    """Issue #3790: Should fill the first (smallest) gap."""
    storage = TodoStorage()

    # IDs [1, 2, 5] - gap at 3 and 4
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=5, text="fifth"),
    ]

    # Should return 3 (smallest gap)
    assert storage.next_id(todos) == 3


def test_next_id_returns_max_plus_one_when_no_gaps() -> None:
    """Issue #3790: When IDs are contiguous, should return max + 1."""
    storage = TodoStorage()

    # Contiguous IDs [1, 2, 3]
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]

    # No gaps, so should return 4
    assert storage.next_id(todos) == 4


def test_next_id_returns_one_for_empty_list() -> None:
    """Issue #3790: Empty list should return 1 as first ID."""
    storage = TodoStorage()

    # Empty list
    assert storage.next_id([]) == 1


def test_next_id_handles_single_element() -> None:
    """Issue #3790: Single todo with id=5 should return 1 as smallest unused."""
    storage = TodoStorage()

    # Single todo with non-1 ID
    todos = [Todo(id=5, text="fifth")]

    # Should return 1 as it's the smallest unused
    assert storage.next_id(todos) == 1


def test_next_id_handles_large_gap_at_start() -> None:
    """Issue #3790: Large gap at the start should return 1."""
    storage = TodoStorage()

    # IDs start from 100
    todos = [Todo(id=100, text="hundredth")]

    # Should return 1 as the smallest unused positive integer
    assert storage.next_id(todos) == 1
