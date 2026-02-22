"""Regression test for issue #5083: next_id 可能产生重复 ID（非原子性）.

This test suite verifies that concurrent add operations produce unique IDs,
addressing the race condition between next_id() and save().

The issue occurs when:
1. Process A calls next_id(todos) and gets ID=2
2. Process B calls next_id(todos) and also gets ID=2
3. Both processes save their todos, resulting in duplicate IDs
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_race_condition_demonstration(tmp_path) -> None:
    """Demonstrate the race condition in next_id.

    This test shows that two processes can get the same ID when
    they both call next_id on the same initial state.
    """
    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Start with one todo
    storage.save([Todo(id=1, text="initial")])

    # Two separate storage instances load the same state
    storage_a = TodoStorage(str(db))
    storage_b = TodoStorage(str(db))

    # Both load the current todos
    todos_a = storage_a.load()
    todos_b = storage_b.load()

    # Both calculate next_id independently
    id_a = storage_a.next_id(todos_a)
    id_b = storage_b.next_id(todos_b)

    # With the race condition, both get the same ID
    assert id_a == id_b, "This demonstrates the race condition - both get the same ID"
    assert id_a == 2, "Expected next_id to return 2"


def test_concurrent_add_produces_unique_ids(tmp_path) -> None:
    """Regression test for issue #5083.

    Tests that multiple processes adding todos concurrently
    produce unique IDs, not duplicate IDs.
    """
    import json

    db = tmp_path / "concurrent_ids.json"

    # Create initial todo
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports the assigned ID."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"worker-{worker_id}-todo")
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

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Load final state and check for unique IDs
    # Note: Due to last-writer-wins, we may not have all todos,
    # but the IDs assigned should still be unique
    assigned_ids = [r[2] for r in successes]

    # Check that the final file contains no duplicate IDs
    if db.exists():
        with open(db, encoding="utf-8") as f:
            final_data = json.load(f)

        ids_in_file = [todo["id"] for todo in final_data]
        unique_ids = set(ids_in_file)

        # The key assertion: no duplicate IDs in the final file
        assert len(ids_in_file) == len(unique_ids), (
            f"Duplicate IDs detected in final file! "
            f"IDs: {ids_in_file}, unique: {unique_ids}"
        )


def test_concurrent_add_with_barrier_stress(tmp_path) -> None:
    """Stress test for issue #5083.

    Uses a barrier to maximize race condition likelihood by having
    all workers start at exactly the same time.
    """
    import json
    import time

    db = tmp_path / "stress.json"

    # Create initial todo
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    # Use a barrier to synchronize workers
    num_workers = 10
    barrier = multiprocessing.Barrier(num_workers)

    def add_worker_sync(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that waits for barrier then adds todo."""
        try:
            # Wait for all workers to be ready
            barrier.wait(timeout=5)

            app = TodoApp(db_path=str(db))
            todo = app.add(f"sync-worker-{worker_id}-todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Start all workers
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker_sync, args=(i, result_queue))
        processes.append(p)
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

    # At minimum, some should succeed
    assert len(successes) > 0, "No workers succeeded"

    # Check for unique IDs in assigned values
    assigned_ids = [r[2] for r in successes]
    unique_assigned = set(assigned_ids)

    # The assigned IDs should be unique
    # (This is the key fix - each add should get a unique ID)
    assert len(assigned_ids) == len(unique_assigned), (
        f"Duplicate IDs assigned to workers! "
        f"Assigned: {assigned_ids}"
    )

    # Check final file for duplicates
    if db.exists():
        with open(db, encoding="utf-8") as f:
            final_data = json.load(f)

        ids_in_file = [todo["id"] for todo in final_data]
        unique_ids = set(ids_in_file)

        assert len(ids_in_file) == len(unique_ids), (
            f"Duplicate IDs in final file! "
            f"IDs: {ids_in_file}"
        )
