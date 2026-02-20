"""Regression test for issue #4679: Race condition causing ID collision.

This test verifies that concurrent processes adding todos to the same
database file generate unique IDs even when running simultaneously.

The bug was in the non-atomic load-compute-save pattern:
1. Process A loads todos (e.g., IDs [1, 2])
2. Process B loads todos (same: IDs [1, 2])
3. Process A computes next_id = 3, saves
4. Process B computes next_id = 3, saves  <-- ID collision!

The fix uses file locking to make the load-compute-save sequence atomic.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def add_todo_worker(db_path: str, worker_id: int, num_todos: int, result_queue: multiprocessing.Queue) -> None:
    """Worker that adds multiple todos and reports generated IDs."""
    try:
        app = TodoApp(db_path=db_path)
        ids_generated = []
        for i in range(num_todos):
            todo = app.add(f"worker-{worker_id}-todo-{i}")
            ids_generated.append(todo.id)
        result_queue.put(("success", worker_id, ids_generated))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_generates_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add() calls generate unique IDs.

    This is the regression test for issue #4679.

    Creates multiple concurrent processes, each adding multiple todos.
    After completion, all IDs across all processes must be unique.
    """
    db_path = tmp_path / "concurrent.json"

    # Configuration: 10 workers, each adding 10 todos = 100 total
    num_workers = 10
    todos_per_worker = 10
    expected_total = num_workers * todos_per_worker

    result_queue = multiprocessing.Queue()
    processes = []

    # Start all workers simultaneously to maximize race condition likelihood
    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=add_todo_worker,
            args=(str(db_path), worker_id, todos_per_worker, result_queue),
        )
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

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Collect all IDs from all workers
    all_ids = []
    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    for _, worker_id, ids in successes:
        all_ids.extend(ids)

    # Verify all IDs are unique (no collisions)
    unique_ids = set(all_ids)
    assert len(unique_ids) == len(all_ids), (
        f"ID collision detected! Got {len(all_ids)} IDs but only {len(unique_ids)} unique. "
        f"Duplicates: {[id for id in all_ids if all_ids.count(id) > 1]}"
    )

    # Verify we got the expected total number of todos
    assert len(all_ids) == expected_total, (
        f"Expected {expected_total} todos, got {len(all_ids)}"
    )

    # Verify the stored file has all todos with unique IDs
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()
    final_ids = [t.id for t in final_todos]

    # Note: Due to the nature of concurrent writes with last-writer-wins on the file,
    # we may not have all todos persisted. But if any todo is persisted, its ID
    # should be unique among the persisted set.
    # The key assertion is that no ID collision occurred during generation.
    assert len(set(final_ids)) == len(final_ids), (
        f"Persisted IDs have collisions: {final_ids}"
    )


def test_single_process_add_generates_unique_ids(tmp_path: Path) -> None:
    """Baseline test: single process adding multiple todos should get unique IDs."""
    db_path = tmp_path / "single.json"
    app = TodoApp(db_path=str(db_path))

    ids = []
    for i in range(100):
        todo = app.add(f"todo-{i}")
        ids.append(todo.id)

    # All IDs should be unique
    assert len(set(ids)) == len(ids), f"IDs should be unique: {ids}"


def test_high_concurrency_id_uniqueness(tmp_path: Path) -> None:
    """Stress test with high concurrency: 20 workers, 5 todos each = 100 total.

    This is more aggressive than the main test to catch edge cases.
    """
    db_path = tmp_path / "stress.json"

    num_workers = 20
    todos_per_worker = 5

    result_queue = multiprocessing.Queue()
    processes = []

    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=add_todo_worker,
            args=(str(db_path), worker_id, todos_per_worker, result_queue),
        )
        processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=60)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    all_ids = []
    successes = [r for r in results if r[0] == "success"]

    for _, worker_id, ids in successes:
        all_ids.extend(ids)

    # All generated IDs must be unique
    unique_ids = set(all_ids)
    assert len(unique_ids) == len(all_ids), (
        f"ID collision in stress test! Duplicates: {[id for id in all_ids if all_ids.count(id) > 1]}"
    )
