"""Regression test for issue #5013: next_id should handle negative and zero IDs.

The next_id method should filter out non-positive IDs (<=0) when calculating
the next ID to ensure new todos always receive a positive integer ID >= 1.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_negative_id_returns_positive() -> None:
    """next_id should return 1 when todos contain only negative IDs."""
    storage = TodoStorage(":memory:")

    # All negative IDs
    todos = [Todo(id=-5, text="negative id todo")]
    assert storage.next_id(todos) == 1, "Should return 1 when max ID is negative"


def test_next_id_with_zero_id_returns_positive() -> None:
    """next_id should return 1 when todos contain only zero IDs."""
    storage = TodoStorage(":memory:")

    # ID = 0
    todos = [Todo(id=0, text="zero id todo")]
    assert storage.next_id(todos) == 1, "Should return 1 when max ID is 0"


def test_next_id_mixed_positive_and_negative_returns_correct() -> None:
    """next_id should ignore negative IDs and use max positive ID + 1."""
    storage = TodoStorage(":memory:")

    # Mix of negative and positive IDs
    todos = [Todo(id=-1, text="negative"), Todo(id=3, text="positive")]
    assert storage.next_id(todos) == 4, "Should return max(positive IDs) + 1 = 4"


def test_next_id_mixed_zero_and_positive_returns_correct() -> None:
    """next_id should ignore zero IDs and use max positive ID + 1."""
    storage = TodoStorage(":memory:")

    # Mix of zero and positive IDs
    todos = [Todo(id=0, text="zero"), Todo(id=2, text="positive")]
    assert storage.next_id(todos) == 3, "Should return max(positive IDs) + 1 = 3"


def test_next_id_all_nonpositive_ids_returns_one() -> None:
    """next_id should return 1 when all IDs are non-positive (negative or zero)."""
    storage = TodoStorage(":memory:")

    # Mix of negative and zero IDs
    todos = [
        Todo(id=-10, text="negative one"),
        Todo(id=0, text="zero one"),
        Todo(id=-1, text="negative two"),
    ]
    assert storage.next_id(todos) == 1, "Should return 1 when no positive IDs exist"


def test_next_id_empty_list_returns_one() -> None:
    """next_id should return 1 for empty list (existing behavior)."""
    storage = TodoStorage(":memory:")

    # Empty list
    todos: list[Todo] = []
    assert storage.next_id(todos) == 1, "Should return 1 for empty list"


def test_next_id_normal_positive_ids_returns_correct() -> None:
    """next_id should work correctly with normal positive IDs (existing behavior)."""
    storage = TodoStorage(":memory:")

    # Normal positive IDs
    todos = [Todo(id=1, text="first"), Todo(id=5, text="fifth")]
    assert storage.next_id(todos) == 6, "Should return max ID + 1 = 6"
