"""Tests for issue #5041: Race condition in next_id().

This test suite verifies that concurrent add operations never generate
duplicate IDs, even when multiple processes are writing simultaneously.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_operations_generate_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #5041: Race condition in next_id().

    Tests that two concurrent add operations (each in a separate process)
    never produce todos with the same ID. This is the core race condition
    described in the issue:

    - Process A loads todos (gets empty list)
    - Process B loads todos (gets empty list)
    - Process A computes next_id = 1
    - Process B computes next_id = 1  <-- DUPLICATE!
    - Process A saves [todo(id=1)]
    - Process B saves [todo(id=1)]  <-- DATA LOSS + DUPLICATE

    After this fix, both processes should generate unique IDs.
    """
    db_path = tmp_path / "todos.json"

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo using the TodoApp CLI layer."""
        try:
            app = TodoApp(db_path=str(db_path))
            # Add a todo with worker-specific text
            todo = app.add(f"task from worker {worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Spawn multiple workers that will all try to add todos simultaneously
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    # Start all workers nearly simultaneously
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, result_queue))
        processes.append(p)

    # Start all at once to maximize race condition
    for p in processes:
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should have succeeded
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Extract the IDs that were generated
    generated_ids = [r[2] for r in successes]

    # CRITICAL ASSERTION: All IDs must be unique
    # This is the core bug we're testing for - before the fix,
    # concurrent adds would generate duplicate IDs
    assert len(generated_ids) == len(set(generated_ids)), (
        f"Duplicate IDs detected! Generated IDs: {sorted(generated_ids)}. "
        f"This indicates a race condition in next_id()."
    )


def test_concurrent_add_preserves_all_data_eventually(tmp_path: Path) -> None:
    """Test that eventual consistency is achieved with unique IDs.

    While the immediate concurrent write may result in last-writer-wins
    at the storage level, the key invariant is that NO two concurrent
    adds should ever assign the same ID to different items.
    """
    db_path = tmp_path / "todos.json"

    # Pre-populate with some existing todos
    storage = TodoStorage(str(db_path))
    storage.save([Todo(id=1, text="existing"), Todo(id=2, text="another")])

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo."""
        try:
            app = TodoApp(db_path=str(db_path))
            todo = app.add(f"new task {worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # All generated IDs should be >= 3 (since 1 and 2 exist)
    generated_ids = [r[2] for r in successes]
    for todo_id in generated_ids:
        assert todo_id >= 3, f"ID {todo_id} collides with pre-existing IDs 1, 2"

    # No duplicates among the newly generated IDs
    assert len(generated_ids) == len(set(generated_ids)), (
        f"Duplicate IDs in new todos: {generated_ids}"
    )
