"""Tests for issue #4559: Race condition in next_id producing duplicate IDs.

This test suite verifies that concurrent add() operations cannot produce
todos with duplicate IDs due to race conditions between load/next_id/save.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #4559: Race condition in next_id.

    Tests that multiple processes calling add() concurrently do not
    produce duplicate IDs. Each process should get a unique ID.
    """
    db = tmp_path / "test.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports the resulting ID."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"worker-{worker_id} task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    # Start all workers at approximately the same time
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)

    # Start all processes
    for p in processes:
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded without errors
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Extract all IDs from successful results
    all_ids = [r[2] for r in successes]

    # All IDs should be unique - this is the core assertion for issue #4559
    unique_ids = set(all_ids)
    assert len(unique_ids) == len(all_ids), (
        f"Duplicate IDs detected! Got {len(all_ids)} todos but only {len(unique_ids)} unique IDs. "
        f"IDs: {all_ids}"
    )

    # Verify the final state by loading directly from storage
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # We may have fewer todos than workers due to race conditions (last-writer-wins)
    # but each todo should have a unique ID
    final_ids = [todo.id for todo in final_todos]
    unique_final_ids = set(final_ids)
    assert len(unique_final_ids) == len(final_ids), (
        f"Duplicate IDs in final storage! IDs: {final_ids}"
    )
