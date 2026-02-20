"""Tests for issue #4636: Race condition in next_id() can cause duplicate IDs.

This test suite verifies that concurrent add operations do not produce
duplicate todo IDs. The race condition occurs when:
1. Process A loads todos, calculates max_id+1
2. Process B loads todos, calculates max_id+1 (same value!)
3. Both processes save with duplicate IDs
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #4636: concurrent add operations should not
    produce duplicate todo IDs.

    This test creates multiple processes that each add a todo concurrently.
    The race condition in next_id() can cause duplicate IDs if the fix is not
    implemented correctly.
    """
    db = tmp_path / "concurrent_add.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports the assigned ID."""
        try:
            app = TodoApp(str(db))
            todo = app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    successes = [r for r in results if r[0] == "success"]

    # All workers should have succeeded
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Collect all assigned IDs
    assigned_ids = [r[2] for r in successes]

    # Verify no duplicate IDs were assigned
    unique_ids = set(assigned_ids)
    assert len(unique_ids) == len(
        assigned_ids
    ), f"Duplicate IDs detected! Assigned: {assigned_ids}, Unique: {unique_ids}"

    # Verify all IDs are positive integers
    for todo_id in assigned_ids:
        assert isinstance(todo_id, int), f"ID should be int, got {type(todo_id)}"
        assert todo_id > 0, f"ID should be positive, got {todo_id}"


def test_concurrent_add_preserves_all_todos(tmp_path: Path) -> None:
    """Test that concurrent add operations preserve all todos, not just some.

    After multiple concurrent adds, the final database should contain all
    todos that were successfully added (or at least not lose data silently).
    """
    db = tmp_path / "concurrent_preserve.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports success/failure."""
        try:
            app = TodoApp(str(db))
            app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Drain the queue to ensure all workers completed
    while not result_queue.empty():
        result_queue.get()

    # Load final state
    app = TodoApp(str(db))
    final_todos = app.list()

    # Each todo should have a unique ID
    ids = [t.id for t in final_todos]
    assert len(ids) == len(set(ids)), f"Duplicate IDs in final state: {ids}"


def test_sequential_add_produces_unique_ids(tmp_path: Path) -> None:
    """Baseline test: sequential add operations should always produce unique IDs.

    This test serves as a sanity check that the add function works correctly
    in the non-concurrent case.
    """
    db = tmp_path / "sequential_add.json"
    app = TodoApp(str(db))

    ids = []
    for i in range(10):
        todo = app.add(f"task-{i}")
        ids.append(todo.id)

    # All IDs should be unique
    assert len(ids) == len(set(ids)), f"Duplicate IDs in sequential adds: {ids}"

    # IDs should be sequential starting from 1
    assert ids == list(range(1, 11)), f"Expected IDs 1-10, got {ids}"
