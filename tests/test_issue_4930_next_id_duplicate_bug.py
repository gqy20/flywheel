"""Regression test for issue #4930: next_id can generate duplicate IDs.

Bug: next_id used max() + 1 without checking if the new ID already exists.
This caused duplicate IDs when loaded data contained negative IDs.

Fix: next_id now finds the smallest unused positive integer.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_avoids_duplicate_with_negative_ids() -> None:
    """Bug #4930: next_id should not generate duplicate IDs when negative IDs exist.

    Previously: max([-1, 1, 2]) + 1 = 3 (OK in this case)
    But: max([-5, -1]) + 1 = 0, which is not positive (or 1)
    Also: max([-5, 5]) + 1 = 6, but IDs 1-5 are available (inefficient)
    """
    storage = TodoStorage("/dev/null")  # Path doesn't matter for next_id

    # Case: negative IDs only - should return 1 (smallest positive)
    todos = [Todo(id=-1, text="negative 1"), Todo(id=-5, text="negative 5")]
    next_id = storage.next_id(todos)
    assert next_id == 1, f"Expected 1, got {next_id}"


def test_next_id_finds_smallest_unused_positive() -> None:
    """Bug #4930: next_id should find the smallest unused positive integer.

    Previously: max([1, 10]) + 1 = 11 (inefficient)
    Now: should return 2 (smallest unused positive)
    """
    storage = TodoStorage("/dev/null")

    # Case: non-sequential IDs - should return smallest gap
    todos = [Todo(id=1, text="one"), Todo(id=5, text="five"), Todo(id=10, text="ten")]
    next_id = storage.next_id(todos)
    assert next_id == 2, f"Expected 2 (smallest unused), got {next_id}"


def test_next_id_handles_mixed_positive_and_negative() -> None:
    """Bug #4930: next_id should handle mixed positive and negative IDs."""
    storage = TodoStorage("/dev/null")

    # Case: mixed IDs including negative
    todos = [
        Todo(id=-1, text="neg"),
        Todo(id=1, text="one"),
        Todo(id=3, text="three"),
    ]
    next_id = storage.next_id(todos)
    assert next_id == 2, f"Expected 2, got {next_id}"


def test_next_id_empty_list_returns_1() -> None:
    """Edge case: empty list should return 1."""
    storage = TodoStorage("/dev/null")

    next_id = storage.next_id([])
    assert next_id == 1, f"Expected 1 for empty list, got {next_id}"


def test_next_id_sequential_returns_next() -> None:
    """Normal case: sequential IDs should return next in sequence."""
    storage = TodoStorage("/dev/null")

    todos = [Todo(id=1, text="one"), Todo(id=2, text="two"), Todo(id=3, text="three")]
    next_id = storage.next_id(todos)
    assert next_id == 4, f"Expected 4, got {next_id}"


def test_next_id_never_returns_existing_id() -> None:
    """Bug #4930: Verify next_id never returns an ID that already exists."""
    storage = TodoStorage("/dev/null")

    # Various edge cases
    test_cases = [
        ([1, 5, 10], 2),  # Gap at 2
        ([1, 2, 3], 4),   # Sequential
        ([-1, -2, -3], 1),  # All negative
        ([0, 1, 2], 3),   # Includes 0
        ([100, 200], 1),  # Large gaps
    ]

    for ids, expected in test_cases:
        todos = [Todo(id=i, text=f"todo-{i}") for i in ids]
        next_id = storage.next_id(todos)
        assert next_id == expected, f"For IDs {ids}, expected {expected}, got {next_id}"
        assert next_id not in ids, f"next_id {next_id} already exists in {ids}"
