"""Regression test for issue #5625: Race condition in concurrent add operations.

This test verifies that concurrent add() operations do not produce duplicate IDs.
The race condition occurs when:
1. Process A loads todos
2. Process B loads todos (same state as A)
3. Both calculate next_id based on same data -> same ID
4. Both save with duplicate IDs

Fix: Use optimistic concurrency with retry on ID collision.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_operations_no_duplicate_ids(tmp_path: Path) -> None:
    """Regression test for issue #5625: Concurrent add() operations should not produce duplicate IDs.

    This test creates multiple processes that each call add() concurrently.
    The bug occurs when two processes load the same todo list, calculate the same
    next_id, and both save with duplicate IDs.

    The fix should ensure that:
    1. ID collision is detected during save
    2. A retry mechanism assigns a new unique ID
    3. All concurrent adds result in unique IDs
    """
    db_path = tmp_path / "todos.json"
    num_workers = 10
    items_per_worker = 3

    def add_worker(worker_id: int, db_path_str: str, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds todos and reports assigned IDs."""
        try:
            app = TodoApp(db_path=db_path_str)
            assigned_ids = []
            for i in range(items_per_worker):
                todo = app.add(f"worker-{worker_id}-item-{i}")
                assigned_ids.append(todo.id)
            result_queue.put(("success", worker_id, assigned_ids))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=add_worker,
            args=(i, str(db_path), result_queue)
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

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    if errors:
        pytest.fail(f"Workers encountered errors: {errors}")

    # Collect all assigned IDs from successful workers
    successes = [r for r in results if r[0] == "success"]
    all_ids = []
    for success in successes:
        _, _, assigned_ids = success
        all_ids.extend(assigned_ids)

    # Verify: All IDs should be unique (no duplicates)
    expected_total = num_workers * items_per_worker
    unique_ids = set(all_ids)

    assert len(all_ids) == expected_total, (
        f"Expected {expected_total} IDs total, got {len(all_ids)}. "
        f"Some adds may have failed silently."
    )

    assert len(unique_ids) == len(all_ids), (
        f"Duplicate IDs detected! "
        f"Expected {len(all_ids)} unique IDs but got only {len(unique_ids)}. "
        f"Duplicates: {[id for id in all_ids if all_ids.count(id) > 1]}"
    )

    # Verify: Final storage should have all items with unique IDs
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()
    final_ids = [t.id for t in final_todos]

    # All final IDs should also be unique
    assert len(set(final_ids)) == len(final_ids), (
        f"Storage contains duplicate IDs: "
        f"{[id for id in final_ids if final_ids.count(id) > 1]}"
    )


def test_concurrent_add_with_initial_todos_no_collision(tmp_path: Path) -> None:
    """Test concurrent add() with existing todos to ensure ID collision is handled.

    This test starts with some existing todos and then runs concurrent adds.
    The race condition can occur when:
    - Initial state: todos with IDs [1, 2, 3]
    - Process A loads, sees next_id=4
    - Process B loads, sees next_id=4 (same!)
    - Both try to save with ID=4

    The fix should detect collision and retry with a new ID.
    """
    db_path = tmp_path / "todos.json"

    # Set up initial todos
    app = TodoApp(db_path=str(db_path))
    for i in range(1, 4):
        app.add(f"initial-todo-{i}")

    num_workers = 5

    def add_worker(worker_id: int, db_path_str: str, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports assigned ID."""
        try:
            app = TodoApp(db_path=db_path_str)
            todo = app.add(f"concurrent-{worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run workers concurrently
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=add_worker,
            args=(i, str(db_path), result_queue)
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

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    if errors:
        pytest.fail(f"Workers encountered errors: {errors}")

    # Collect all assigned IDs
    successes = [r for r in results if r[0] == "success"]
    all_ids = [r[2] for r in successes]

    # All concurrent adds should have unique IDs
    assert len(set(all_ids)) == len(all_ids), (
        f"Duplicate IDs in concurrent adds! "
        f"IDs: {all_ids}, Unique: {set(all_ids)}"
    )

    # No concurrent ID should collide with initial IDs [1, 2, 3]
    for id in all_ids:
        assert id > 3, f"ID {id} collides with initial IDs"

    # Final verification: all IDs in storage should be unique
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()
    final_ids = [t.id for t in final_todos]

    assert len(set(final_ids)) == len(final_ids), (
        f"Storage has duplicate IDs: {final_ids}"
    )
    assert len(final_todos) == 3 + num_workers  # 3 initial + num_workers concurrent
