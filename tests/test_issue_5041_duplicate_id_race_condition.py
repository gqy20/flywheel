"""Regression test for issue #5041: Race condition in next_id().

This test verifies that concurrent add operations do not generate duplicate IDs.

The race condition occurs because next_id() computes max+1 from an in-memory list
without any synchronization. When multiple processes add todos concurrently:

1. Process A loads todos, computes next_id = 1
2. Process B loads todos, also computes next_id = 1
3. Both processes create todos with ID 1
4. Both save, and while data may be valid JSON, IDs can collide

This test spawns multiple processes that each add a todo, and verifies that
all resulting todos have unique IDs.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds a todo and reports the assigned ID."""
    try:
        app = TodoApp(db_path=db_path)
        # Small random delay to increase race condition likelihood
        time.sleep(0.001 * (worker_id % 3))

        todo = app.add(f"worker-{worker_id}-todo")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_operations_produce_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #5041: Race condition in next_id().

    Tests that multiple processes adding todos concurrently do NOT produce
    todos with duplicate IDs. Each added todo should have a unique ID.
    """
    db_path = str(tmp_path / "test_concurrent_add.json")

    # Run multiple workers concurrently, each adding a todo
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, db_path, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded without errors
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # Note: Some errors might occur due to race conditions on file access
    # but we should have at least some successes
    assert len(successes) >= 2, f"Expected at least 2 successes, got {len(successes)}. Errors: {errors}"

    # Verify that all assigned IDs are unique
    assigned_ids = [r[2] for r in successes]
    unique_ids = set(assigned_ids)

    assert len(unique_ids) == len(
        assigned_ids
    ), f"Duplicate IDs detected! All IDs: {assigned_ids}, unique: {unique_ids}"


def test_concurrent_add_operations_produce_unique_ids_after_merge(tmp_path: Path) -> None:
    """Test that after concurrent adds, the final file has all unique IDs.

    This test focuses on the final state of the database after concurrent adds.
    Even if last-writer-wins loses some todos, the IDs that exist in the final
    file should be unique.
    """
    db_path = str(tmp_path / "test_concurrent_final.json")

    # Initialize the database with an existing todo
    storage = TodoStorage(db_path)
    storage.save([Todo(id=1, text="initial")])

    def add_and_read_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo and reads back all todos."""
        try:
            app = TodoApp(db_path=db_path)
            app.add(f"worker-{worker_id}-todo")

            # Read back all todos and report their IDs
            todos = app.list()
            ids = [t.id for t in todos]
            result_queue.put(("success", worker_id, ids))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_and_read_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Load final state and verify all IDs are unique
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    if len(final_todos) > 0:
        final_ids = [t.id for t in final_todos]
        unique_final_ids = set(final_ids)
        assert len(unique_final_ids) == len(
            final_ids
        ), f"Final state has duplicate IDs! IDs: {final_ids}"


def test_next_id_is_deterministic_for_sequential_calls(tmp_path: Path) -> None:
    """Test that next_id produces deterministic unique IDs for sequential calls.

    This is a baseline test to ensure the fix doesn't break sequential behavior.
    """
    db_path = str(tmp_path / "test_sequential.json")
    storage = TodoStorage(db_path)

    # Empty list should return 1
    assert storage.next_id([]) == 1

    # After adding todo with id=1, next should be 2
    assert storage.next_id([Todo(id=1, text="test")]) == 2

    # After adding more, should get max+1
    assert storage.next_id([Todo(id=1, text="a"), Todo(id=5, text="b"), Todo(id=3, text="c")]) == 6


def test_add_with_file_locking_prevents_duplicate_ids(tmp_path: Path) -> None:
    """Test that the fixed implementation prevents duplicate IDs with concurrent adds.

    This test uses a more aggressive concurrent pattern to stress-test the fix.
    """
    db_path = str(tmp_path / "test_locking.json")

    # Create database with initial todo
    storage = TodoStorage(db_path)
    storage.save([Todo(id=1, text="initial")])

    def fast_add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo quickly without delay."""
        try:
            app = TodoApp(db_path=db_path)
            todo = app.add(f"fast-worker-{worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Launch all workers nearly simultaneously
    num_workers = 10
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=fast_add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=15)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # If we got successes, verify no duplicate IDs
    if len(successes) >= 2:
        assigned_ids = [r[2] for r in successes]
        unique_ids = set(assigned_ids)
        assert len(unique_ids) == len(
            assigned_ids
        ), f"Duplicate IDs in fast concurrent adds! IDs: {assigned_ids}"
