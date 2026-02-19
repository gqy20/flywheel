"""Regression tests for issue #4549.

Issue: from_dict allows negative IDs and zero IDs, but storage.next_id
assumes IDs are positive integers, potentially causing next_id to
return non-positive values.

Fix: Ensure next_id always returns at least 1 by filtering out non-positive IDs.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_empty_list_returns_1() -> None:
    """next_id([]) should return 1, not 0 or negative."""
    storage = TodoStorage()
    assert storage.next_id([]) == 1


def test_next_id_with_negative_ids_returns_1() -> None:
    """When all IDs are negative, next_id should return 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=-5, text="negative id"),
        Todo(id=-1, text="another negative"),
    ]
    assert storage.next_id(todos) == 1


def test_next_id_with_zero_id_returns_next_positive() -> None:
    """When ID is 0, next_id should still return a positive integer."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="zero id")]
    assert storage.next_id(todos) == 1


def test_next_id_with_mixed_positive_and_negative_ids() -> None:
    """Mixed IDs: next_id should find the max positive and add 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=-10, text="negative"),
        Todo(id=0, text="zero"),
        Todo(id=5, text="positive"),
        Todo(id=-3, text="another negative"),
    ]
    # Max positive is 5, so next_id should be 6
    assert storage.next_id(todos) == 6


def test_next_id_with_only_zero_returns_1() -> None:
    """When the only ID is 0, next_id should return 1."""
    storage = TodoStorage()
    todos = [Todo(id=0, text="only zero")]
    assert storage.next_id(todos) == 1


def test_next_id_with_negative_and_zero_only_returns_1() -> None:
    """When IDs are only negative or zero, next_id should return 1."""
    storage = TodoStorage()
    todos = [
        Todo(id=-1, text="negative"),
        Todo(id=0, text="zero"),
    ]
    assert storage.next_id(todos) == 1


def test_next_id_preserves_normal_behavior() -> None:
    """Normal positive IDs should still work as expected."""
    storage = TodoStorage()
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
    ]
    assert storage.next_id(todos) == 3
