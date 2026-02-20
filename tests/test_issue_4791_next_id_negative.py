"""Tests for issue #4791: next_id() returns incorrect value when max todo ID is negative."""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_returns_1_for_empty_list() -> None:
    """next_id([]) should return 1."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_returns_1_when_max_id_is_negative() -> None:
    """Bug #4791: next_id([Todo(id=-5, ...)]) should return 1, not -4."""
    storage = TodoStorage()
    todos = [Todo(id=-5, text="test")]
    # The next_id should be at least 1, regardless of negative IDs
    assert storage.next_id(todos) == 1


def test_next_id_returns_max_plus_1_for_positive_ids() -> None:
    """next_id([Todo(id=5, ...)]) should return 6."""
    storage = TodoStorage()
    todos = [Todo(id=5, text="test")]
    assert storage.next_id(todos) == 6


def test_next_id_handles_mixed_positive_and_negative_ids() -> None:
    """When todos have mixed positive/negative IDs, use max positive ID."""
    storage = TodoStorage()
    todos = [Todo(id=-10, text="negative"), Todo(id=3, text="positive")]
    assert storage.next_id(todos) == 4


def test_next_id_allows_default_id_start() -> None:
    """When all IDs are non-positive, next_id should return 1."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero"), Todo(id=-1, text="negative")]
    assert storage.next_id(todos) == 1
