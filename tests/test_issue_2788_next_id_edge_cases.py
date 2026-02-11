"""Tests for issue #2788: next_id() returns different values for empty vs non-empty list with max id 0.

The bug is a redundant ternary operator that makes the code unnecessarily complex.
This test verifies that next_id() behaves consistently across edge cases.
"""

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Issue #2788: next_id([]) should return 1."""
    storage = TodoStorage()
    result = storage.next_id([])
    assert result == 1, f"Expected next_id([]) to return 1, got {result}"


def test_next_id_list_with_id_0_returns_1() -> None:
    """Issue #2788: next_id([Todo(id=0)]) should return 1."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="x")]
    result = storage.next_id(todos)
    assert result == 1, f"Expected next_id([Todo(id=0)]) to return 1, got {result}"


def test_next_id_list_with_id_1_returns_2() -> None:
    """Issue #2788: next_id([Todo(id=1)]) should return 2."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="x")]
    result = storage.next_id(todos)
    assert result == 2, f"Expected next_id([Todo(id=1)]) to return 2, got {result}"


def test_next_id_list_with_multiple_ids_returns_max_plus_1() -> None:
    """Issue #2788: next_id should return max(id) + 1 for multiple todos."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=5, text="c")]
    result = storage.next_id(todos)
    assert result == 6, f"Expected next_id([1,2,5]) to return 6, got {result}"


def test_next_id_consistency_empty_vs_zero_id() -> None:
    """Issue #2788: next_id should return the same value for [] and [Todo(id=0)]."""
    storage = TodoStorage()
    empty_result = storage.next_id([])
    zero_id_result = storage.next_id([Todo(id=0, text="x")])
    assert empty_result == zero_id_result, (
        f"next_id() should return the same value for empty list and list with id=0. "
        f"Got empty={empty_result}, zero_id={zero_id_result}"
    )
