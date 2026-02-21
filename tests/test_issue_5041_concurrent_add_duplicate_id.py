"""Regression tests for Issue #5041: Race condition in next_id().

This test file ensures that concurrent add operations never produce
todos with duplicate IDs.

The issue: next_id() computes max+1 from in-memory list without any lock.
In cli.py add(), there's a race window between load() and save() where
two concurrent processes can both compute the same next_id.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

from flywheel.cli import TodoApp


def _add_todo_worker(
    worker_id: int,
    db_path: str,
    result_queue: multiprocessing.Queue,
    barrier: multiprocessing.Barrier,
) -> None:
    """Worker function that adds a todo and reports the assigned ID.

    Uses a barrier to maximize race condition likelihood by having all workers
    start at exactly the same time.
    """
    try:
        # Wait for all workers to be ready - this maximizes race window overlap
        barrier.wait()

        app = TodoApp(db_path=db_path)
        todo = app.add(f"Task from worker {worker_id}")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_operations_produce_unique_ids() -> None:
    """Two concurrent add operations should never produce duplicate IDs.

    This is the regression test for issue #5041.

    The race condition occurs when:
    1. Process A loads todos, calculates next_id=2
    2. Process B loads todos, calculates next_id=2 (same as A!)
    3. Process A saves todo with id=2
    4. Process B saves todo with id=2 (duplicate!)

    With proper file locking, this should never happen.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "test.json")

        # Create initial todo so next_id starts at 2
        app = TodoApp(db_path=db_path)
        initial = app.add("Initial task")
        assert initial.id == 1

        # Spawn multiple workers that each add a todo concurrently
        num_workers = 4
        processes = []
        result_queue = multiprocessing.Queue()
        barrier = multiprocessing.Barrier(num_workers)

        for i in range(num_workers):
            p = multiprocessing.Process(
                target=_add_todo_worker, args=(i, db_path, result_queue, barrier)
            )
            processes.append(p)
            p.start()

        # Wait for all processes to complete
        for p in processes:
            p.join(timeout=10)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # All workers should have succeeded
        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(successes) == num_workers, (
            f"Expected {num_workers} successes, got {len(successes)}"
        )

        # Extract the IDs assigned to each worker
        assigned_ids = [r[2] for r in successes]

        # Critical assertion: all IDs must be unique
        # This is the bug we're testing for - without proper locking,
        # concurrent adds can produce duplicate IDs
        unique_ids = set(assigned_ids)
        assert len(unique_ids) == len(assigned_ids), (
            f"Duplicate IDs detected! Got IDs: {sorted(assigned_ids)}. "
            f"This indicates a race condition in next_id()."
        )

        # Also verify the final state is consistent
        final_todos = app.list()
        # We should have initial + num_workers todos
        assert len(final_todos) == num_workers + 1

        # All IDs in storage should be unique
        storage_ids = [t.id for t in final_todos]
        assert len(set(storage_ids)) == len(storage_ids), (
            f"Storage contains duplicate IDs: {sorted(storage_ids)}"
        )


def test_sequential_add_operations_produce_unique_ids() -> None:
    """Sequential add operations should always produce unique IDs.

    This is a baseline test to ensure the fix doesn't break normal operation.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "test.json")
        app = TodoApp(db_path=db_path)

        # Add multiple todos sequentially
        ids = []
        for i in range(10):
            todo = app.add(f"Task {i}")
            ids.append(todo.id)

        # All IDs should be unique
        assert len(set(ids)) == len(ids), f"Duplicate IDs in sequential adds: {ids}"

        # IDs should be sequential starting from 1
        assert ids == list(range(1, 11))


def test_concurrent_add_with_preexisting_todos() -> None:
    """Concurrent adds with pre-existing todos should produce unique IDs.

    Tests the race condition with a more realistic initial state.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "test.json")
        app = TodoApp(db_path=db_path)

        # Create several initial todos
        for i in range(5):
            app.add(f"Initial task {i}")

        # Spawn concurrent workers
        num_workers = 3
        processes = []
        result_queue = multiprocessing.Queue()
        barrier = multiprocessing.Barrier(num_workers)

        for i in range(num_workers):
            p = multiprocessing.Process(
                target=_add_todo_worker, args=(i, db_path, result_queue, barrier)
            )
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=10)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(successes) == num_workers

        assigned_ids = [r[2] for r in successes]
        unique_ids = set(assigned_ids)
        assert len(unique_ids) == len(assigned_ids), (
            f"Duplicate IDs detected! Got IDs: {sorted(assigned_ids)}"
        )

        # Final count should be 5 initial + 3 concurrent = 8
        final_todos = app.list()
        assert len(final_todos) == 8
