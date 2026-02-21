"""Tests for ID uniqueness during concurrent operations.

This test suite verifies that concurrent add() operations produce unique IDs
even when multiple processes are writing to the same database file.

Related issue: #4859 - Race condition in next_id() when used concurrently
"""

from __future__ import annotations

import multiprocessing

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path) -> None:
    """Regression test for issue #4859: Race condition producing duplicate IDs.

    Multiple processes calling add() concurrently should each receive unique
    IDs. Without proper locking, two processes might:
    1. Both load the same todos list
    2. Both compute the same next_id()
    3. Both save their todo with duplicate IDs

    This test verifies that all resulting todos have unique IDs.
    """
    db = tmp_path / "concurrent_ids.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports the assigned ID."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    # Start all workers at roughly the same time to maximize race condition
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

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # Print errors for debugging if any
    if errors:
        for e in errors:
            print(f"Worker {e[1]} error: {e[2]}")

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Collect all IDs that were assigned
    assigned_ids = [r[2] for r in successes]

    # Verify all IDs are unique - this is the key assertion for issue #4859
    unique_ids = set(assigned_ids)
    assert len(unique_ids) == len(
        assigned_ids
    ), f"Duplicate IDs detected! IDs: {assigned_ids}, Unique: {unique_ids}"

    # Also verify the final file state has unique IDs
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    final_ids = [todo.id for todo in final_todos]
    unique_final_ids = set(final_ids)

    # The final file should have the same number of todos as workers
    # (if no data was lost to race conditions)
    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos in final file, got {len(final_todos)}. "
        f"Some todos may have been lost due to race conditions."
    )

    # All final IDs should be unique
    assert len(unique_final_ids) == len(final_ids), (
        f"Final file contains duplicate IDs! IDs: {final_ids}"
    )


def test_concurrent_add_with_existing_todos(tmp_path) -> None:
    """Test that concurrent add() works correctly when there are existing todos.

    This tests the scenario where:
    1. Some todos already exist in the database
    2. Multiple processes add new todos concurrently
    3. All new IDs should be unique and not conflict with existing IDs
    """
    db = tmp_path / "concurrent_with_existing.json"

    # Pre-populate with existing todos
    storage = TodoStorage(str(db))
    existing_todos = [
        Todo(id=1, text="existing-1"),
        Todo(id=2, text="existing-2"),
        Todo(id=5, text="existing-5"),  # Non-contiguous IDs
    ]
    storage.save(existing_todos)

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports the assigned ID."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"new-worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run workers concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=15)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers

    # Verify new IDs don't conflict with existing IDs
    new_ids = [r[2] for r in successes]
    existing_ids = {1, 2, 5}

    for new_id in new_ids:
        assert new_id not in existing_ids, (
            f"New ID {new_id} conflicts with existing IDs {existing_ids}"
        )

    # Verify all new IDs are unique
    assert len(set(new_ids)) == len(new_ids), f"Duplicate new IDs detected: {new_ids}"
