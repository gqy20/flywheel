"""Regression test for issue #5611: next_id() can return duplicate IDs with gaps.

When todos have non-contiguous IDs (e.g., due to deletion), next_id() should
still return a unique ID that doesn't collide with existing IDs.

The current max+1 pattern fails to fill gaps, which can lead to confusing
ID sequences. The fix ensures next_id() finds the first available ID.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_fills_gap_when_ids_not_contiguous(tmp_path: Path) -> None:
    """Test that next_id() finds first available ID when there are gaps.

    Given todos with IDs [1, 3, 5], next_id() should return 2 (the first
    gap), not 6 (max+1). This ensures IDs are reused and remain compact.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos with non-contiguous IDs (simulating deletions)
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),  # ID 2 was deleted
        Todo(id=5, text="fifth"),  # ID 4 was deleted
    ]

    # next_id() should return 2 (first available), not 6
    next_id = storage.next_id(todos)
    assert next_id == 2, f"Expected ID 2 to fill gap, got {next_id}"


def test_next_id_returns_1_for_empty_list(tmp_path: Path) -> None:
    """Test that next_id() returns 1 for an empty todo list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    next_id = storage.next_id([])
    assert next_id == 1, f"Expected ID 1 for empty list, got {next_id}"


def test_next_id_returns_next_after_max_when_no_gaps(tmp_path: Path) -> None:
    """Test that next_id() returns max+1 when there are no gaps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Contiguous IDs starting from 1
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]

    next_id = storage.next_id(todos)
    assert next_id == 4, f"Expected ID 4 (max+1), got {next_id}"


def test_next_id_with_single_gap_at_start(tmp_path: Path) -> None:
    """Test next_id() when lowest ID is not 1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # IDs start at 3 (1 and 2 were deleted)
    todos = [
        Todo(id=3, text="third"),
        Todo(id=4, text="fourth"),
    ]

    # Should return 1, the first available ID
    next_id = storage.next_id(todos)
    assert next_id == 1, f"Expected ID 1 to fill first gap, got {next_id}"


def test_next_id_with_multiple_gaps(tmp_path: Path) -> None:
    """Test next_id() fills first gap when there are multiple gaps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Multiple gaps: 2, 4, 6 are missing
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
        Todo(id=5, text="fifth"),
        Todo(id=7, text="seventh"),
    ]

    # Should return 2 (first gap), not 8
    next_id = storage.next_id(todos)
    assert next_id == 2, f"Expected ID 2 (first gap), got {next_id}"


def test_sequential_adds_with_gaps_produce_unique_ids(tmp_path: Path) -> None:
    """Integration test: sequential adds should produce unique IDs even with gaps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Start with non-contiguous IDs
    todos = [
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
    ]

    # Simulate adding multiple todos sequentially
    ids_used = set(todo.id for todo in todos)

    for i in range(5):
        new_id = storage.next_id(todos)
        assert new_id not in ids_used, f"Duplicate ID generated: {new_id}"
        ids_used.add(new_id)
        todos.append(Todo(id=new_id, text=f"new-{i}"))

    # Verify all IDs are unique
    all_ids = [todo.id for todo in todos]
    assert len(all_ids) == len(set(all_ids)), "All IDs should be unique"
