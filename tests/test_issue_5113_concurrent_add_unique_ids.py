"""Regression test for issue #5113: Race condition in add() - duplicate IDs.

This test verifies that concurrent add() operations from multiple processes
produce todos with unique IDs, even under race conditions.

Issue: https://github.com/gqy20/flywheel/issues/5113
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker that adds a todo and returns the ID assigned."""
    try:
        app = TodoApp(db_path=db_path)
        # Add small staggered delay to increase race condition likelihood
        time.sleep(0.001 * (worker_id % 3))
        todo = app.add(f"worker-{worker_id}-todo")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add() operations produce unique todo IDs.

    This is the regression test for issue #5113. Before the fix, concurrent
    add() operations could produce duplicate IDs because:
    1. Process A loads [], computes next_id=1
    2. Process B loads [], computes next_id=1 (same!)
    3. Both save, last-writer-wins, but both have ID=1

    After the fix, all concurrent adds should produce unique IDs.
    """
    db_path = tmp_path / "concurrent.json"

    num_workers = 8
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, str(db_path), result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should succeed
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers failed: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Verify all IDs are unique (this is the core assertion for #5113)
    ids_assigned = [r[2] for r in successes]
    assert len(ids_assigned) == len(set(ids_assigned)), (
        f"Duplicate IDs detected! IDs: {ids_assigned}, unique: {set(ids_assigned)}"
    )

    # Verify final file state has unique IDs too
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()
    final_ids = [t.id for t in final_todos]

    # Due to last-writer-wins, we might have fewer todos than workers
    # But all IDs in the file should be unique
    assert len(final_ids) == len(set(final_ids)), (
        f"Duplicate IDs in final file! IDs: {final_ids}"
    )


def test_sequential_add_produces_monotonic_ids(tmp_path: Path) -> None:
    """Baseline test: sequential adds should produce monotonic increasing IDs."""
    app = TodoApp(db_path=str(tmp_path / "test.json"))

    ids = []
    for i in range(10):
        todo = app.add(f"todo-{i}")
        ids.append(todo.id)

    assert ids == list(range(1, 11)), f"Expected IDs 1-10, got {ids}"


def test_concurrent_add_produces_monotonically_increasing_ids(tmp_path: Path) -> None:
    """Test that after concurrent adds, all IDs are monotonically assignable.

    After concurrent adds complete, the next ID should be greater than all
    existing IDs, ensuring no ID collision for future operations.
    """
    db_path = tmp_path / "monotonic.json"

    # Do concurrent adds
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, str(db_path), result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Now do a sequential add - its ID should not conflict
    app = TodoApp(db_path=str(db_path))
    new_todo = app.add("after-concurrent")

    # Verify the new ID doesn't conflict with any existing
    storage = TodoStorage(str(db_path))
    all_todos = storage.load()
    all_ids = [t.id for t in all_todos]

    # Should appear exactly once
    assert all_ids.count(new_todo.id) == 1, (
        f"New todo ID {new_todo.id} appears multiple times or not at all in {all_ids}"
    )
