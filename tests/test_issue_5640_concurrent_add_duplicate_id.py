"""Regression test for issue #5640: Duplicate ID generation in concurrent add operations.

This test verifies that concurrent add operations from multiple processes
produce unique IDs and do not result in ID collisions.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


# Module-level function for multiprocessing with spawn context
def _add_worker(worker_id: int, db_path: str, result_file: str) -> None:
    """Worker that adds a todo and reports the assigned ID."""
    try:
        app = TodoApp(db_path=db_path)
        todo = app.add(f"todo from worker {worker_id}")
        # Write result to file instead of queue to avoid context issues
        with open(result_file, "a") as f:
            f.write(f"success,{worker_id},{todo.id}\n")
    except Exception as e:
        with open(result_file, "a") as f:
            f.write(f"error,{worker_id},{e}\n")


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #5640: Concurrent add operations should produce unique IDs.

    This test spawns multiple processes that each add a todo concurrently.
    After all processes complete, the final storage should have no duplicate IDs.

    Without proper synchronization, a race condition can occur:
    1. Process A loads todos [id=1]
    2. Process B loads todos [id=1]
    3. Process A calculates next_id = 2, adds todo with id=2
    4. Process B calculates next_id = 2, adds todo with id=2
    5. Process A saves todos
    6. Process B saves todos (overwriting A's save)
    Result: Duplicate id=2 in the final file
    """
    db_path = tmp_path / "test_concurrent.json"
    result_file = tmp_path / "results.txt"

    # Initialize with one todo
    storage = TodoStorage(str(db_path))
    storage.save([Todo(id=1, text="initial")])

    num_processes = 5

    # Use spawn context to test true cross-process concurrency
    ctx = multiprocessing.get_context("spawn")
    processes = []
    for i in range(num_processes):
        p = ctx.Process(target=_add_worker, args=(i, str(db_path), str(result_file)))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results from file
    results = []
    if result_file.exists():
        with open(result_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(",", 2)
                    results.append((parts[0], int(parts[1]), parts[2] if parts[0] == "error" else int(parts[2])))

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should have succeeded
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_processes, f"Expected {num_processes} successes, got {len(successes)}"

    # Collect all IDs assigned to new todos
    assigned_ids = [r[2] for r in successes]

    # All assigned IDs should be unique (no duplicates)
    assert len(assigned_ids) == len(set(assigned_ids)), (
        f"Duplicate IDs detected! Assigned IDs: {sorted(assigned_ids)}. "
        f"This indicates a race condition in ID generation."
    )

    # Load final storage and verify no duplicate IDs exist
    final_todos = storage.load()
    final_ids = [todo.id for todo in final_todos]

    # Should have initial todo + num_processes new todos
    assert len(final_ids) == len(set(final_ids)), (
        f"Duplicate IDs in final storage! IDs: {sorted(final_ids)}. "
        f"Some todos were lost due to last-writer-wins race."
    )


def test_concurrent_add_preserves_all_todos(tmp_path: Path) -> None:
    """Verify that concurrent adds preserve all todos (no data loss).

    This is a stronger test that ensures:
    1. No duplicate IDs
    2. No data loss from race conditions
    """
    db_path = tmp_path / "test_no_data_loss.json"
    result_file = tmp_path / "results2.txt"

    # Start with empty storage
    storage = TodoStorage(str(db_path))

    num_processes = 3

    ctx = multiprocessing.get_context("spawn")
    processes = []
    for i in range(num_processes):
        p = ctx.Process(target=_add_worker, args=(i, str(db_path), str(result_file)))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    if result_file.exists():
        with open(result_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(",", 2)
                    results.append((parts[0], int(parts[1]), parts[2] if parts[0] == "error" else int(parts[2])))

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify all todos were saved (no data loss)
    final_todos = storage.load()

    # Due to race conditions without proper locking, we might lose some todos
    # With proper locking, all should be preserved
    assert len(final_todos) == num_processes, (
        f"Expected {num_processes} todos, got {len(final_todos)}. "
        f"Some todos were lost due to race conditions."
    )
