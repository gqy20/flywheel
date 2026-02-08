"""Regression test for issue #2291: next_id() returns correct value for empty list.

Bug: next_id() logic bug returned 2 for empty list instead of 1 due to redundant conditional.
Fix: Simplified to `return max((todo.id for todo in todos), default=0) + 1`
"""

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_empty_list_returns_1() -> None:
    """Issue #2291: next_id([]) should return 1, not 2."""
    storage = TodoStorage()
    empty_todos: list[Todo] = []
    assert storage.next_id(empty_todos) == 1, "Empty list should return ID 1"


def test_next_id_single_todo_returns_2() -> None:
    """Issue #2291: next_id([Todo(id=1)]) should return 2."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first")]
    assert storage.next_id(todos) == 2, "Single todo with id=1 should return ID 2"


def test_next_id_non_contiguous_returns_max_plus_1() -> None:
    """Issue #2291: next_id([Todo(id=1), Todo(id=5)]) should return 6."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="first"), Todo(id=5, text="fifth")]
    assert storage.next_id(todos) == 6, "Should return max(id) + 1"
