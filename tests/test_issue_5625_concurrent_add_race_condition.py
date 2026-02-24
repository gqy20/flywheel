"""Regression test for issue #5625: Race condition in concurrent add operations.

This test verifies that concurrent add() operations do not produce duplicate IDs.
The fix implements optimistic concurrency control with retry on ID collision.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _add_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds a todo and reports the assigned ID."""
    try:
        app = TodoApp(db_path=db_path)
        todo = app.add(f"worker-{worker_id}-todo")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_no_duplicate_ids(tmp_path: Path) -> None:
    """Regression test for issue #5625.

    Tests that multiple processes calling add() concurrently do not produce
    duplicate IDs. Each process should get a unique ID through optimistic
    concurrency control with retry on collision.
    """
    db_path = tmp_path / "concurrent_add.json"

    # Initialize with empty file
    storage = TodoStorage(str(db_path))
    storage.save([])

    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    # Start all workers nearly simultaneously
    for i in range(num_workers):
        p = multiprocessing.Process(target=_add_worker, args=(i, str(db_path), result_queue))
        processes.append(p)

    # Start all processes quickly to maximize race condition
    for p in processes:
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Verify all IDs are unique - this is the core assertion for issue #5625
    ids = [r[2] for r in successes]
    assert len(ids) == len(set(ids)), f"Duplicate IDs detected: {ids}"

    # Verify we can load all todos with unique IDs
    loaded_todos = storage.load()
    assert len(loaded_todos) == num_workers

    loaded_ids = [todo.id for todo in loaded_todos]
    assert len(loaded_ids) == len(set(loaded_ids)), f"Duplicate IDs in storage: {loaded_ids}"


def test_concurrent_add_sequential_ids(tmp_path: Path) -> None:
    """Verify that concurrent adds produce sequential IDs starting from 1."""
    db_path = tmp_path / "sequential_ids.json"

    # Initialize with empty file
    storage = TodoStorage(str(db_path))
    storage.save([])

    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=_add_worker, args=(i, str(db_path), result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Collect and verify
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    ids = sorted([r[2] for r in results if r[0] == "success"])

    # IDs should be 1, 2, 3, 4, 5 (sequential)
    assert ids == list(range(1, num_workers + 1)), f"Expected sequential IDs 1-{num_workers}, got {ids}"


def test_single_process_add_is_still_correct(tmp_path: Path) -> None:
    """Verify that the fix doesn't break single-process add behavior."""
    db_path = tmp_path / "single_process.json"
    app = TodoApp(db_path=str(db_path))

    # Add multiple todos sequentially
    todo1 = app.add("first")
    todo2 = app.add("second")
    todo3 = app.add("third")

    assert todo1.id == 1
    assert todo2.id == 2
    assert todo3.id == 3

    # Verify persistence
    todos = app.list()
    assert len(todos) == 3
    assert [t.id for t in todos] == [1, 2, 3]
