"""Tests for issue #4559: Race condition in next_id producing duplicate IDs.

This test suite verifies that concurrent add() operations cannot produce
todos with duplicate IDs, which would happen if two processes:
1. Load the same todo list
2. Calculate the same next_id
3. Both save, resulting in duplicate IDs

The fix uses file locking to ensure atomicity of the load-calculate-save sequence.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #4559: Race condition with concurrent add() operations.

    Tests that when multiple processes call add() concurrently, all resulting
    todos have unique IDs. Without file locking, two processes could:
    1. Load the same todo list (e.g., both see [id=1])
    2. Calculate the same next_id (both calculate 2)
    3. Both save, resulting in duplicate IDs [1, 2, 2]
    """
    db = tmp_path / "concurrent_add.json"

    # Pre-populate with one todo to ensure we have a baseline
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial todo")])

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo via TodoApp.add()."""
        try:
            app = TodoApp(db_path=str(db))
            # Small stagger to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))
            todo = app.add(f"worker-{worker_id} todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
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

    if errors:
        error_msgs = [f"Worker {r[1]}: {r[2]}" for r in errors]
        pytest.fail(f"Some workers encountered errors: {error_msgs}")

    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}"
    )

    # Load final state and verify all IDs are unique
    final_storage = TodoStorage(str(db))
    final_todos = final_storage.load()

    all_ids = [todo.id for todo in final_todos]
    unique_ids = set(all_ids)

    # The critical assertion: no duplicate IDs
    assert len(all_ids) == len(unique_ids), (
        f"Duplicate IDs detected! "
        f"Total todos: {len(all_ids)}, Unique IDs: {len(unique_ids)}. "
        f"Duplicates: {[i for i in all_ids if all_ids.count(i) > 1]}"
    )

    # Also verify we have the expected number of todos (initial + workers)
    assert len(final_todos) == num_workers + 1, (
        f"Expected {num_workers + 1} todos (1 initial + {num_workers} added), "
        f"got {len(final_todos)}. Some writes may have been lost."
    )

    # Verify all worker IDs were assigned
    worker_assigned_ids = {r[2] for r in successes}
    expected_worker_ids = set(range(2, num_workers + 2))  # IDs 2 through num_workers+1
    assert worker_assigned_ids == expected_worker_ids, (
        f"Unexpected ID assignments. Expected: {expected_worker_ids}, "
        f"Got: {worker_assigned_ids}"
    )


def test_concurrent_add_with_existing_todos(tmp_path: Path) -> None:
    """Test concurrent add() when there are existing todos with non-sequential IDs.

    This tests a more complex scenario where IDs may not be sequential
    (e.g., after deletions), ensuring the race condition is still prevented.
    """
    db = tmp_path / "concurrent_add_existing.json"
    storage = TodoStorage(str(db))

    # Create todos with gaps in IDs (simulating deletions)
    storage.save([
        Todo(id=1, text="first"),
        Todo(id=5, text="fifth"),  # Gap: IDs 2,3,4 missing
        Todo(id=10, text="tenth"),  # Gap: IDs 6,7,8,9 missing
    ])

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo via TodoApp.add()."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"worker-{worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run concurrent workers
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    if errors:
        error_msgs = [f"Worker {r[1]}: {r[2]}" for r in errors]
        pytest.fail(f"Some workers encountered errors: {error_msgs}")

    assert len(successes) == num_workers

    # Verify all IDs are unique
    final_todos = storage.load()
    all_ids = [todo.id for todo in final_todos]
    unique_ids = set(all_ids)

    assert len(all_ids) == len(unique_ids), (
        f"Duplicate IDs detected! IDs: {all_ids}"
    )

    # We should have 3 original + num_workers new todos
    assert len(final_todos) == 3 + num_workers
