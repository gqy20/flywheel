"""Tests for issue #4999: next_id produces invalid ID when todos contain negative IDs.

Bug: next_id uses max() without validating that existing IDs are positive.
If a negative ID like -5 exists, next_id returns -4, which violates the
implicit ID >= 1 contract.

Fix: next_id should filter to only positive IDs when computing max.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_empty_list_returns_1() -> None:
    """next_id should return 1 when the todos list is empty."""
    storage = TodoStorage()
    todos: list[Todo] = []
    assert storage.next_id(todos) == 1


def test_next_id_with_negative_ids_only_returns_1() -> None:
    """next_id should return 1 when all existing IDs are negative.

    This is the core bug case: if all IDs are negative, max() would return
    a negative number, and +1 would still be invalid (e.g., -5 -> -4).
    The fix ensures we return 1 in this case.
    """
    storage = TodoStorage()
    todos = [Todo(id=-5, text="negative 1"), Todo(id=-3, text="negative 2")]
    assert storage.next_id(todos) == 1


def test_next_id_with_mixed_positive_and_negative_ids() -> None:
    """next_id should ignore negative IDs and compute max from positive IDs only.

    Given IDs [1, -5, 3], the max positive ID is 3, so next_id should return 4.
    """
    storage = TodoStorage()
    todos = [Todo(id=1, text="positive 1"), Todo(id=-5, text="negative"), Todo(id=3, text="positive 2")]
    assert storage.next_id(todos) == 4


def test_next_id_with_normal_positive_ids_returns_max_plus_1() -> None:
    """next_id should return max(existing_ids) + 1 for normal positive IDs.

    This ensures the fix doesn't break the existing behavior for positive IDs.
    Given IDs [1, 2], next_id should return 3.
    """
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=2, text="second")]
    assert storage.next_id(todos) == 3


def test_next_id_with_zero_id_returns_1_or_max_plus_1() -> None:
    """next_id should treat 0 as non-positive and ignore it.

    If the only ID is 0, next_id should return 1.
    If there are positive IDs and 0, next_id should return max(positive) + 1.
    """
    storage = TodoStorage()
    # Only 0 - should return 1
    todos = [Todo(id=0, text="zero")]
    assert storage.next_id(todos) == 1

    # 0 and positive IDs - should ignore 0
    todos = [Todo(id=0, text="zero"), Todo(id=2, text="positive")]
    assert storage.next_id(todos) == 3
