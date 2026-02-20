"""Regression test for issue #4805: next_id should return positive ID when storage has negative IDs."""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list() -> None:
    """When todos is empty list, next_id should return 1."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_returns_max_plus_one_for_positive_ids() -> None:
    """When todos contains [1, 2, 5], next_id should return 6."""
    storage = TodoStorage()
    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=5, text="c")]
    assert storage.next_id(todos) == 6


def test_next_id_ignores_negative_ids() -> None:
    """Bug #4805: When todos contains negative IDs, next_id should return based on positive IDs only."""
    storage = TodoStorage()
    # If we have todos with IDs -5 and 1, next_id should return 2 (max positive + 1)
    # NOT -4 (which would happen if we just used max() on all IDs)
    todos = [Todo(id=-5, text="negative"), Todo(id=1, text="positive")]
    assert storage.next_id(todos) == 2


def test_next_id_returns_1_when_only_negative_ids() -> None:
    """When todos only contains negative IDs, next_id should return 1."""
    storage = TodoStorage()
    todos = [Todo(id=-5, text="x"), Todo(id=-10, text="y")]
    assert storage.next_id(todos) == 1


def test_next_id_handles_mixed_positive_and_negative_ids() -> None:
    """When todos contains [1, 10] with some negative IDs, next_id should return 11."""
    storage = TodoStorage()
    todos = [
        Todo(id=-100, text="negative1"),
        Todo(id=1, text="positive1"),
        Todo(id=10, text="positive2"),
        Todo(id=-5, text="negative2"),
    ]
    assert storage.next_id(todos) == 11
