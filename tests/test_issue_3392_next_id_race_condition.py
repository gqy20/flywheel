"""Regression test for issue #3392: Race condition in next_id() causing ID collisions.

The race condition occurs when:
1. Process A loads todos [id=1], calculates next_id=2
2. Process B loads todos [id=1], calculates next_id=2 (same!)
3. Both processes save todos with duplicate id=2

The fix should ensure that concurrent add operations result in unique IDs.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for #3392: Concurrent add operations should produce unique IDs.

    This test creates multiple processes that all perform add operations concurrently
    on the same database file. The expected behavior is that all resulting todos
    have unique IDs with no duplicates.
    """
    db_path = str(tmp_path / "concurrent.json")

    # Create initial todo so there's something to read
    app = TodoApp(db_path)
    initial = app.add("initial todo")
    assert initial.id == 1

    num_workers = 5
    num_adds_per_worker = 3

    def add_worker(worker_id: int, db: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that performs multiple add operations concurrently."""
        try:
            app = TodoApp(db)
            added_ids = []
            for i in range(num_adds_per_worker):
                todo = app.add(f"worker-{worker_id}-todo-{i}")
                added_ids.append(todo.id)
                # Small delay to increase chance of race condition
                time.sleep(0.001)
            result_queue.put(("success", worker_id, added_ids))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Start all workers at roughly the same time
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, db_path, result_queue))
        processes.append(p)

    for p in processes:
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check no errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Load final state and check for unique IDs
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # Collect all IDs
    all_ids = [todo.id for todo in final_todos]

    # All IDs should be unique - no duplicates
    unique_ids = set(all_ids)
    assert len(all_ids) == len(unique_ids), (
        f"ID collision detected! Got {len(all_ids)} todos but only {len(unique_ids)} unique IDs. "
        f"Duplicates: {all_ids} -> unique: {unique_ids}"
    )

    # Verify we have the expected number of todos (1 initial + num_workers * num_adds_per_worker)
    expected_count = 1 + (num_workers * num_adds_per_worker)
    assert len(final_todos) == expected_count, (
        f"Expected {expected_count} todos, got {len(final_todos)}. Data may have been lost."
    )


def test_concurrent_add_single_operation_each(tmp_path: Path) -> None:
    """Simpler test: each worker performs exactly one add operation.

    This isolates the race condition more precisely.
    """
    db_path = str(tmp_path / "concurrent_simple.json")

    # Start with empty database
    num_workers = 10

    def single_add(worker_id: int, db: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that performs a single add operation."""
        try:
            app = TodoApp(db)
            # Small random-ish delay to synchronize start times
            time.sleep(0.001 * (worker_id % 5))
            todo = app.add(f"worker-{worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Start all workers
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=single_add, args=(i, db_path, result_queue))
        processes.append(p)
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check no errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Load final state
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # All IDs should be unique
    all_ids = [todo.id for todo in final_todos]
    unique_ids = set(all_ids)

    assert len(all_ids) == len(unique_ids), (
        f"ID collision detected! Got {len(all_ids)} todos but only {len(unique_ids)} unique IDs. "
        f"All IDs: {sorted(all_ids)}"
    )

    # All workers should have completed
    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos, got {len(final_todos)}"
    )


def test_sequential_add_produces_incrementing_ids(tmp_path: Path) -> None:
    """Baseline test: sequential add operations should work correctly.

    This test verifies that the fix doesn't break normal sequential operations.
    """
    app = TodoApp(str(tmp_path / "sequential.json"))

    todos = []
    for i in range(10):
        todo = app.add(f"todo-{i}")
        todos.append(todo)

    # All IDs should be sequential and unique
    ids = [t.id for t in todos]
    assert ids == list(range(1, 11)), f"Expected IDs 1-10, got {ids}"


def test_add_with_lock_context_manager(tmp_path: Path) -> None:
    """Test that TodoStorage.lock() context manager works correctly.

    This verifies the lock-based fix works for single-process scenarios.
    """
    db_path = str(tmp_path / "locked.json")

    # Create initial state
    storage = TodoStorage(db_path)
    storage.save([Todo(id=1, text="initial")])

    # Test that we can use the lock context manager
    with storage.lock():
        todos = storage.load()
        new_id = storage.next_id(todos)
        todos.append(Todo(id=new_id, text="new todo"))
        storage.save(todos)

    # Verify the add worked
    final_todos = storage.load()
    assert len(final_todos) == 2
    all_ids = [todo.id for todo in final_todos]
    assert len(set(all_ids)) == 2, f"All IDs should be unique: {all_ids}"
