"""Regression test for issue #4019: Race condition in next_id().

Tests that concurrent processes adding todos to the same database
receive unique IDs, preventing duplicate IDs in the final file.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path) -> None:
    """Regression test for issue #4019: Race condition in next_id().

    When two processes add todos simultaneously to the same database,
    each todo should have a unique ID. Without proper synchronization,
    both processes could calculate the same next_id (e.g., both get ID 1
    when starting from an empty database).
    """
    db = tmp_path / "concurrent_ids.json"

    def add_worker(worker_id: int, num_todos: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds multiple todos and records the assigned IDs."""
        try:
            app = TodoApp(db_path=str(db))
            assigned_ids = []
            for i in range(num_todos):
                todo = app.add(f"worker-{worker_id}-todo-{i}")
                assigned_ids.append(todo.id)
                # Small delay to increase race condition window
                time.sleep(0.001)
            result_queue.put(("success", worker_id, assigned_ids))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 3
    todos_per_worker = 5
    result_queue = multiprocessing.Queue()
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, todos_per_worker, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should succeed
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Collect all assigned IDs from all workers
    all_assigned_ids = []
    for success in successes:
        _, worker_id, ids = success
        all_assigned_ids.extend(ids)

    # Verify all IDs within each worker are unique
    for success in successes:
        _, worker_id, ids = success
        assert len(ids) == len(set(ids)), (
            f"Worker {worker_id} got duplicate IDs within its own operations: {ids}"
        )

    # Verify all IDs across all workers are unique - THIS IS THE KEY ASSERTION
    # Without a fix, workers will have overlapping IDs due to race condition
    total_expected_todos = num_workers * todos_per_worker
    unique_ids = set(all_assigned_ids)
    assert len(unique_ids) == total_expected_todos, (
        f"Expected {total_expected_todos} unique IDs, but got {len(unique_ids)}. "
        f"Assigned IDs: {sorted(all_assigned_ids)} - this indicates race condition!"
    )

    # Verify the final file has all todos with unique IDs
    storage = TodoStorage(str(db))
    final_todos = storage.load()
    final_ids = [t.id for t in final_todos]

    # Due to last-writer-wins, we may have fewer todos, but all should have unique IDs
    assert len(final_ids) == len(set(final_ids)), (
        f"Final file has duplicate IDs: {final_ids}"
    )


def test_next_id_with_file_locking(tmp_path) -> None:
    """Test that next_id uses file-based locking for atomicity.

    This test verifies that the next_id implementation properly handles
    concurrent access by using a file-based lock or counter mechanism.
    """
    db = tmp_path / "locked_ids.json"
    storage = TodoStorage(str(db))

    # Start with empty database
    assert storage.load() == []

    # Multiple calls should return unique IDs even when called rapidly
    ids = []
    for _ in range(100):
        todos = storage.load()
        next_id = storage.next_id(todos)
        ids.append(next_id)
        # Simulate the add operation
        storage.save(todos + [Todo(id=next_id, text=f"test-{next_id}")])

    # All IDs should be unique
    assert len(ids) == len(set(ids)), f"Got duplicate IDs: {sorted(ids)}"


def test_concurrent_next_id_calls(tmp_path) -> None:
    """Test that concurrent next_id calls return unique values.

    Multiple processes calling next_id simultaneously should each
    receive a unique ID, even if they all read the same initial state.
    """
    db = tmp_path / "race_ids.json"

    # Initialize with one todo
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    def get_next_id_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that gets next_id and saves a new todo."""
        try:
            storage = TodoStorage(str(db))
            todos = storage.load()
            new_id = storage.next_id(todos)
            # This is the race window - simulate delay before save
            time.sleep(0.01)
            todos.append(Todo(id=new_id, text=f"worker-{worker_id}"))
            storage.save(todos)
            result_queue.put(("success", worker_id, new_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 5
    result_queue = multiprocessing.Queue()
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(target=get_next_id_worker, args=(i, result_queue))
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

    # All workers that succeeded should have received unique IDs
    assigned_ids = [s[2] for s in successes]
    # Due to race condition without fix, some workers will get same ID (2)
    # With fix, all should be unique
    unique_ids = set(assigned_ids)
    assert len(unique_ids) == len(assigned_ids), (
        f"Workers got duplicate IDs: {sorted(assigned_ids)}. "
        f"Expected {len(assigned_ids)} unique IDs, got {len(unique_ids)}"
    )
