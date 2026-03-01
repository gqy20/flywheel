"""Regression test for issue #6604: Race condition in ID generation.

The next_id() method computes a new ID based on the current max ID in the
provided list. Under concurrent access (two processes calling add() simultaneously),
both can read the same max ID and generate the same new ID, causing duplicate IDs.

This test verifies that file-based locking prevents this race condition.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _concurrent_add_worker(
    db_path: str,
    worker_id: int,
    num_adds: int,
    result_queue: multiprocessing.Queue,
) -> None:
    """Worker function that adds todos concurrently to the same database.

    Each worker adds `num_adds` todos with unique text identifying the worker.
    Results are put in the result_queue for verification.
    """
    try:
        app = TodoApp(db_path=db_path)
        added_ids = []

        for i in range(num_adds):
            # Small delay to increase chance of race condition
            time.sleep(0.001 * (i % 3))
            todo = app.add(f"worker-{worker_id}-todo-{i}")
            added_ids.append(todo.id)

        result_queue.put(("success", worker_id, added_ids))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add() operations produce unique IDs.

    This is the main regression test for issue #6604.

    Acceptance criteria:
    - Two concurrent add() operations should not produce todos with the same ID
    - All IDs from both processes should be unique after completion
    """
    db_path = tmp_path / "concurrent_test.json"

    num_workers = 2
    adds_per_worker = 50
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start workers with slight stagger to increase race likelihood
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(
            target=_concurrent_add_worker,
            args=(str(db_path), i, adds_per_worker, result_queue),
        )
        processes.append(p)
        p.start()
        # Small stagger to ensure workers overlap
        time.sleep(0.01)

    # Wait for all workers
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers, f"Expected {num_workers} successes"

    # Collect all IDs from all workers
    all_ids: list[int] = []
    for _, worker_id, ids in successes:
        assert len(ids) == adds_per_worker, (
            f"Worker {worker_id} only added {len(ids)}/{adds_per_worker} todos"
        )
        all_ids.extend(ids)

    # Verify no duplicate IDs - this is the core assertion for issue #6604
    unique_ids = set(all_ids)
    assert len(unique_ids) == len(all_ids), (
        f"Duplicate IDs detected! Total: {len(all_ids)}, Unique: {len(unique_ids)}. "
        f"Missing uniqueness indicates race condition in next_id()."
    )

    # Verify the storage has all todos with correct IDs
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()
    final_ids = [todo.id for todo in final_todos]
    assert len(final_ids) == len(set(final_ids)), "Final storage contains duplicate IDs"


def test_concurrent_add_with_existing_todos(tmp_path: Path) -> None:
    """Test concurrent adds when database already has existing todos.

    Ensures ID generation correctly accounts for existing IDs under concurrency.
    """
    db_path = tmp_path / "concurrent_with_existing.json"

    # Pre-populate with some todos
    storage = TodoStorage(str(db_path))
    from flywheel.todo import Todo

    existing_todos = [
        Todo(id=1, text="existing-1"),
        Todo(id=5, text="existing-5"),
        Todo(id=10, text="existing-10"),
    ]
    storage.save(existing_todos)

    num_workers = 2
    adds_per_worker = 20
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(
            target=_concurrent_add_worker,
            args=(str(db_path), i, adds_per_worker, result_queue),
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers

    # All newly generated IDs should be > 10 (max existing ID)
    all_new_ids: list[int] = []
    for _, worker_id, ids in successes:
        all_new_ids.extend(ids)

    for new_id in all_new_ids:
        assert new_id > 10, f"New ID {new_id} should be greater than max existing ID 10"

    # Verify no duplicates with existing IDs
    final_todos = storage.load()
    all_final_ids = [todo.id for todo in final_todos]
    assert len(all_final_ids) == len(set(all_final_ids)), "Duplicate IDs in final state"
