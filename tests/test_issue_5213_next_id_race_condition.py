"""Regression test for issue #5213: Race condition in next_id().

Tests that concurrent add operations generate unique IDs, preventing duplicate IDs
when multiple processes add todos simultaneously.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_generates_unique_ids(tmp_path) -> None:
    """Regression test for issue #5213: Concurrent add operations should generate unique IDs.

    When multiple processes simultaneously add todos, each should get a unique ID.
    Without proper synchronization, concurrent processes could read the same todo
    snapshot and both calculate the same next_id, resulting in duplicate IDs.
    """
    db = tmp_path / "concurrent_todos.json"

    def add_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo and reports the assigned ID."""
        try:
            app = TodoApp(db_path)
            todo = app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, str(db), result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=15)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Verify all IDs are unique
    assigned_ids = [r[2] for r in successes]
    assert len(assigned_ids) == len(set(assigned_ids)), (
        f"Duplicate IDs detected! All IDs should be unique. Got: {sorted(assigned_ids)}"
    )

    # Verify we can load all todos and each has a unique ID
    storage = TodoStorage(str(db))
    todos = storage.load()

    # We may have fewer todos than workers due to last-writer-wins,
    # but all IDs in the stored file should still be unique
    stored_ids = [todo.id for todo in todos]
    assert len(stored_ids) == len(set(stored_ids)), (
        f"Duplicate IDs in stored data! IDs: {stored_ids}"
    )
