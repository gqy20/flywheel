"""Tests for issue #3893: next_id() behavior with non-contiguous IDs."""

from __future__ import annotations

import tempfile
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_with_non_contiguous_ids() -> None:
    """Issue #3893: next_id() should return max+1 for non-contiguous IDs."""
    with tempfile.TemporaryDirectory() as tmp:
        storage = TodoStorage(str(Path(tmp) / "test.json"))
        todos = [Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=10, text="c")]
        # Should return 11, not 2 or 4
        assert storage.next_id(todos) == 11


def test_next_id_after_deletion_empty_list() -> None:
    """Issue #3893: next_id() should return 1 for empty list (all deleted)."""
    with tempfile.TemporaryDirectory() as tmp:
        storage = TodoStorage(str(Path(tmp) / "test.json"))
        # When all todos are deleted, the list is empty
        # Expected behavior: return 1 (restart from beginning)
        assert storage.next_id([]) == 1


def test_next_id_with_single_high_id() -> None:
    """Issue #3893: next_id() should handle single high ID correctly."""
    with tempfile.TemporaryDirectory() as tmp:
        storage = TodoStorage(str(Path(tmp) / "test.json"))
        todos = [Todo(id=100, text="only high id")]
        # Should return 101, not 1
        assert storage.next_id(todos) == 101


def test_next_id_with_gap_at_start() -> None:
    """Issue #3893: next_id() should handle gap at start (no id=1)."""
    with tempfile.TemporaryDirectory() as tmp:
        storage = TodoStorage(str(Path(tmp) / "test.json"))
    todos = [Todo(id=50, text="starts at 50"), Todo(id=75, text="then 75")]
    # Should return 76 (max+1), not 1
    assert storage.next_id(todos) == 76


def test_next_id_monotonic_increment() -> None:
    """Issue #3893: next_id() should be monotonically increasing (no reuse)."""
    with tempfile.TemporaryDirectory() as tmp:
        storage = TodoStorage(str(Path(tmp) / "test.json"))
    # After creating and "deleting" ids 1,2,3, remaining has id=5
    # next_id should be 6, not 1 (no ID reuse)
    todos = [Todo(id=5, text="remaining after deletions")]
    assert storage.next_id(todos) == 6
