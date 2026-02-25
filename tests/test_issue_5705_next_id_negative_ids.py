"""Regression tests for issue #5705: next_id returns duplicate IDs with negative/non-contiguous IDs.

Bug: next_id returns duplicate IDs when existing todos have non-contiguous or negative IDs.
Location: src/flywheel/storage.py:128
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_negative_id_returns_1() -> None:
    """If JSON contains [{'id':-5, 'text':'x'}], next_id should return 1 instead of -4.

    Negative IDs should not affect next_id calculation - we want positive IDs only.
    """
    storage = TodoStorage()
    todos = [Todo(id=-5, text="negative todo")]

    # next_id should return 1 (first positive ID) not -4
    assert storage.next_id(todos) == 1


def test_next_id_with_zero_id_returns_1() -> None:
    """If JSON contains [{'id':0, 'text':'x'}], next_id should return 1.

    ID 0 is not valid, so next_id should still return 1.
    """
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero id todo")]

    # next_id should return 1 (first valid positive ID)
    assert storage.next_id(todos) == 1


def test_next_id_with_non_contiguous_ids_returns_next() -> None:
    """If JSON contains [{'id':100, 'text':'x'}], next_id should return 101.

    Non-contiguous IDs should still work correctly.
    """
    storage = TodoStorage()
    todos = [Todo(id=100, text="high id todo")]

    # next_id should return 101
    assert storage.next_id(todos) == 101


def test_next_id_with_mixed_positive_and_negative_ids() -> None:
    """Mixed positive and negative IDs should only consider positive IDs."""
    storage = TodoStorage()
    todos = [
        Todo(id=-10, text="negative"),
        Todo(id=-5, text="negative2"),
        Todo(id=3, text="positive"),
    ]

    # max positive ID is 3, so next should be 4
    assert storage.next_id(todos) == 4


def test_next_id_with_only_negative_ids_returns_1() -> None:
    """If all IDs are negative, next_id should return 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=-100, text="negative1"),
        Todo(id=-50, text="negative2"),
        Todo(id=-1, text="negative3"),
    ]

    # No positive IDs, so return 1
    assert storage.next_id(todos) == 1


def test_next_id_with_gap_in_ids_returns_next_after_max() -> None:
    """If there are gaps in IDs (e.g., 1, 5, 10), next_id should return max+1.

    Note: The current behavior uses max+1, not filling gaps. This test documents
    that behavior and ensures negative IDs don't break it.
    """
    storage = TodoStorage()
    todos = [
        Todo(id=1, text="first"),
        Todo(id=5, text="fifth"),
        Todo(id=10, text="tenth"),
    ]

    # max positive ID is 10, so next should be 11 (not 2 to fill the gap)
    assert storage.next_id(todos) == 11


def test_next_id_empty_list_returns_1() -> None:
    """Empty list should return 1 (existing behavior, should remain unchanged)."""
    storage = TodoStorage()
    todos: list[Todo] = []

    assert storage.next_id(todos) == 1
