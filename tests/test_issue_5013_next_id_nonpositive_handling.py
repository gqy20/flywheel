"""Tests for issue #5013: next_id should handle non-positive IDs.

The next_id method should filter out negative IDs and ID=0 when computing
the next ID, to prevent generating IDs that are <= 0 or causing conflicts.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_negative_id_returns_1() -> None:
    """next_id should return 1 when todos contain only negative IDs.

    Bug: Previously returned -4 for [Todo(id=-5)].
    Fix: Filter out non-positive IDs before computing max.
    """
    storage = TodoStorage("/tmp/test.json")  # Path doesn't matter for next_id
    todos = [Todo(id=-5, text="negative id")]

    result = storage.next_id(todos)

    assert result == 1, f"Expected 1, got {result}"


def test_next_id_with_zero_id_returns_1() -> None:
    """next_id should return 1 when todos contain only ID=0.

    Bug: Previously returned 1, but this is correct only if there's
    no positive ID. The fix ensures ID=0 is filtered out consistently.
    """
    storage = TodoStorage("/tmp/test.json")
    todos = [Todo(id=0, text="zero id")]

    result = storage.next_id(todos)

    assert result == 1, f"Expected 1, got {result}"


def test_next_id_with_mixed_positive_negative_ids() -> None:
    """next_id should ignore negative IDs and return max(positive_id) + 1.

    Bug: Previously returned 4 for [Todo(id=-1), Todo(id=3)].
    Fix: Filter out negative IDs, then max positive ID (3) + 1 = 4.
    """
    storage = TodoStorage("/tmp/test.json")
    todos = [
        Todo(id=-1, text="negative"),
        Todo(id=3, text="positive"),
    ]

    result = storage.next_id(todos)

    assert result == 4, f"Expected 4, got {result}"


def test_next_id_all_negative_ids_returns_1() -> None:
    """next_id should return 1 when all todos have negative IDs.

    This is the boundary case: no valid positive IDs exist,
    so we start fresh from ID=1.
    """
    storage = TodoStorage("/tmp/test.json")
    todos = [
        Todo(id=-10, text="negative one"),
        Todo(id=-5, text="negative two"),
        Todo(id=-1, text="negative three"),
    ]

    result = storage.next_id(todos)

    assert result == 1, f"Expected 1, got {result}"


def test_next_id_with_zero_and_positive_ids() -> None:
    """next_id should ignore ID=0 and return max(positive_id) + 1."""
    storage = TodoStorage("/tmp/test.json")
    todos = [
        Todo(id=0, text="zero"),
        Todo(id=2, text="positive"),
    ]

    result = storage.next_id(todos)

    assert result == 3, f"Expected 3, got {result}"


def test_next_id_normal_case_unchanged() -> None:
    """Verify normal case still works after fix.

    This is a regression test to ensure the fix doesn't break
    the standard use case.
    """
    storage = TodoStorage("/tmp/test.json")
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=5, text="fifth"),
    ]

    result = storage.next_id(todos)

    assert result == 6, f"Expected 6, got {result}"


def test_next_id_empty_list_returns_1() -> None:
    """Verify empty list case still works after fix."""
    storage = TodoStorage("/tmp/test.json")
    todos: list[Todo] = []

    result = storage.next_id(todos)

    assert result == 1, f"Expected 1, got {result}"
