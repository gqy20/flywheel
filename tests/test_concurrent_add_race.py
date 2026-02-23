"""Regression test for issue #5467: Race condition in next_id() with concurrent add.

Tests that concurrent add() operations produce unique IDs, preventing
the TOCTOU (time-of-check to time-of-use) race condition where:
1. Process A loads todos (empty list)
2. Process B loads todos (empty list)
3. Both compute next_id() -> both get ID 1
4. Both save, resulting in duplicate IDs
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp


def add_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds a todo and reports the assigned ID."""
    try:
        app = TodoApp(db_path=db_path)
        # Small staggered delay to maximize race condition window
        time.sleep(0.001 * (worker_id % 3))
        todo = app.add(f"todo from worker {worker_id}")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for #5467: concurrent add() should produce unique IDs.

    This test spawns multiple processes that each add a todo concurrently.
    Without proper synchronization, these processes may compute the same
    next_id and result in duplicate IDs in the final state.
    """
    db_path = str(tmp_path / "concurrent_add.json")

    # Run multiple concurrent add operations
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, db_path, result_queue))
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
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Critical assertion: All IDs should be unique
    assigned_ids = [r[2] for r in successes]
    unique_ids = set(assigned_ids)

    assert len(unique_ids) == len(
        assigned_ids
    ), f"Duplicate IDs detected! Got IDs: {sorted(assigned_ids)}. Expected {num_workers} unique IDs."


def test_concurrent_add_multiple_iterations(tmp_path: Path) -> None:
    """Run multiple iterations to ensure race condition fix is reliable."""
    for iteration in range(3):
        iteration_path = tmp_path / f"iteration_{iteration}.json"

        processes = []
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        for i in range(3):
            p = multiprocessing.Process(
                target=add_worker, args=(i, str(iteration_path), result_queue)
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

        assert len(errors) == 0, f"Iteration {iteration}: errors {errors}"
        assert len(successes) == 3, f"Iteration {iteration}: expected 3 successes"

        assigned_ids = [r[2] for r in successes]
        assert len(set(assigned_ids)) == len(assigned_ids), (
            f"Iteration {iteration}: Duplicate IDs {sorted(assigned_ids)}"
        )
