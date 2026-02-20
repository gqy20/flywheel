"""Regression test for issue #4679: Race condition in concurrent ID generation.

This test verifies that when multiple processes concurrently add todos,
each todo gets a unique ID without collision.

The bug: The load-compute-save pattern is not atomic:
1. Process A loads todos, computes next_id = max(ids) + 1
2. Process B loads todos, computes same next_id (before A saves)
3. Both processes save with duplicate IDs
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def add_worker(worker_id: int, db_path: str, num_adds: int, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds multiple todos and reports IDs generated."""
    try:
        app = TodoApp(db_path=db_path)
        ids_generated = []
        for i in range(num_adds):
            todo = app.add(f"worker-{worker_id}-todo-{i}")
            ids_generated.append(todo.id)
            # Small delay to increase race condition likelihood
            time.sleep(0.001)
        result_queue.put(("success", worker_id, ids_generated))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for #4679: Concurrent adds must produce unique IDs.

    Creates 10 concurrent processes each adding 10 todos to the same db file.
    Verifies all 100 IDs are unique after completion.
    """
    db = tmp_path / "concurrent.json"
    db_path = str(db)

    # Run multiple workers concurrently, each adding multiple todos
    num_workers = 10
    adds_per_worker = 10
    expected_total = num_workers * adds_per_worker

    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=add_worker,
            args=(i, db_path, adds_per_worker, result_queue)
        )
        processes.append(p)
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

    # Collect all IDs generated
    all_ids = []
    for success in successes:
        _, worker_id, ids = success
        all_ids.extend(ids)

    # THE KEY ASSERTION: All IDs must be unique
    unique_ids = set(all_ids)
    assert len(unique_ids) == len(all_ids), (
        f"ID collision detected! Generated {len(all_ids)} IDs "
        f"but only {len(unique_ids)} are unique. "
        f"Duplicates: {[i for i in all_ids if all_ids.count(i) > 1]}"
    )

    # Verify we got the expected number of unique IDs
    assert len(unique_ids) == expected_total, (
        f"Expected {expected_total} unique IDs, got {len(unique_ids)}"
    )

    # Final verification: load file and check stored IDs
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # All stored IDs should also be unique
    stored_ids = [t.id for t in final_todos]
    assert len(set(stored_ids)) == len(stored_ids), (
        f"Stored IDs have duplicates: {stored_ids}"
    )


def test_concurrent_add_no_id_collision_with_many_processes(tmp_path: Path) -> None:
    """Additional test: 5 processes adding 20 todos each must produce 100 unique IDs."""
    db = tmp_path / "many_concurrent.json"
    db_path = str(db)

    num_workers = 5
    adds_per_worker = 20
    expected_total = num_workers * adds_per_worker

    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=add_worker,
            args=(i, db_path, adds_per_worker, result_queue)
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=60)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    all_ids = []
    for r in results:
        if r[0] == "success":
            all_ids.extend(r[2])

    unique_ids = set(all_ids)
    assert len(unique_ids) == expected_total, (
        f"Expected {expected_total} unique IDs, got {len(unique_ids)}. "
        f"ID collision in concurrent add operations!"
    )
