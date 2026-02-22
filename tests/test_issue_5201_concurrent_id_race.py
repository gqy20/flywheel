"""Regression test for issue #5201: Race condition in next_id().

Tests that concurrent add() operations from multiple processes
generate unique todo IDs without duplicates.

The bug: next_id() computes ID from in-memory todos list after load but
before save, creating a race window where concurrent processes can
generate the same ID.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from flywheel.cli import TodoApp


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #5201.

    Multiple concurrent add() operations must never produce todos with
    the same ID. Each process adds a todo, and all resulting IDs must
    be unique.
    """
    db = tmp_path / "race_test.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo and returns the generated ID."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run 10+ concurrent processes performing add() operations
    num_workers = 12
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
        p.join(timeout=15)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should have succeeded
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert (
        len(successes) == num_workers
    ), f"Expected {num_workers} successes, got {len(successes)}"

    # CRITICAL: All IDs must be unique - no duplicates allowed
    ids = [r[2] for r in successes]
    unique_ids = set(ids)

    if len(unique_ids) != len(ids):
        duplicates = [id for id in ids if ids.count(id) > 1]
        pytest.fail(
            f"Race condition detected! Found duplicate IDs: {duplicates}. "
            f"Expected {num_workers} unique IDs, but got {len(unique_ids)} unique values. "
            f"All IDs: {ids}"
        )

    # Final verification: loading the file should show valid todos
    app = TodoApp(db_path=str(db))
    all_todos = app.list()
    assert len(all_todos) > 0, "Should have some todos saved"
