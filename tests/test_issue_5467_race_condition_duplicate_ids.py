"""Regression test for issue #5467: Race condition in next_id() generating duplicate IDs.

Tests that concurrent add() operations produce unique IDs even when multiple
processes load the same initial state before calculating next_id().

The fix uses file-based locking (fcntl.flock) to ensure atomic ID allocation.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #5467: Two concurrent add() calls should produce different IDs.

    This test simulates the race condition:
    1. Two processes start with the same initial state
    2. Both load the empty todo list simultaneously
    3. Both calculate next_id() as 1 (before fix)
    4. Both save their todos
    5. Result: duplicate IDs = 1

    With the fix, file-based locking ensures only one process at a time
    can calculate and reserve an ID.
    """
    db = tmp_path / "concurrent.json"
    num_processes = 5
    num_iterations = 3

    def add_worker(worker_id: int, iteration: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that calls add() concurrently."""
        try:
            app = TodoApp(db_path=str(db))
            # Small delay to increase chance of race condition
            time.sleep(0.001 * (worker_id % 3))
            todo = app.add(text=f"worker-{worker_id}-iter-{iteration}")
            result_queue.put(("success", worker_id, iteration, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, iteration, str(e)))

    # Run concurrent adds multiple times to increase chance of catching the race
    for iteration in range(num_iterations):
        processes = []
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        for i in range(num_processes):
            p = multiprocessing.Process(target=add_worker, args=(i, iteration, result_queue))
            processes.append(p)
            p.start()

        # Wait for all processes
        for p in processes:
            p.join(timeout=10)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Check for errors
        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"Workers encountered errors: {errors}"

        # Collect IDs from this iteration
        ids_this_iteration = [r[3] for r in results if r[0] == "success"]

        # All IDs within this iteration should be unique
        assert len(ids_this_iteration) == len(set(ids_this_iteration)), (
            f"Iteration {iteration}: Duplicate IDs detected! Got IDs: {ids_this_iteration}"
        )

    # Final verification: load all todos and check no duplicates
    storage = TodoStorage(str(db))
    all_todos = storage.load()

    all_ids = [todo.id for todo in all_todos]
    assert len(all_ids) == len(set(all_ids)), (
        f"Duplicate IDs in final database! "
        f"IDs: {all_ids}, duplicates: {[i for i in all_ids if all_ids.count(i) > 1]}"
    )

    # Verify we have the expected number of todos
    expected_count = num_processes * num_iterations
    assert len(all_todos) == expected_count, (
        f"Expected {expected_count} todos, got {len(all_todos)}"
    )


def test_concurrent_add_on_empty_db(tmp_path: Path) -> None:
    """Simpler test: spawn 2 processes adding to empty DB, verify different IDs.

    This is the minimal test case from the issue description.
    """
    db = tmp_path / "empty.json"

    def add_todo(text: str, result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(text=text)
            result_queue.put(("success", todo.id, todo.text))
        except Exception as e:
            result_queue.put(("error", str(e)))

    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start two processes simultaneously
    p1 = multiprocessing.Process(target=add_todo, args=("todo1", result_queue))
    p2 = multiprocessing.Process(target=add_todo, args=("todo2", result_queue))

    p1.start()
    p2.start()

    p1.join(timeout=10)
    p2.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Both should succeed
    assert len(results) == 2, f"Expected 2 results, got {len(results)}: {results}"

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Errors encountered: {errors}"

    # IDs must be different
    id1, id2 = results[0][1], results[1][1]
    assert id1 != id2, f"Both processes got the same ID: {id1}"

    # Final check
    storage = TodoStorage(str(db))
    todos = storage.load()
    assert len(todos) == 2
    ids = [t.id for t in todos]
    assert ids == [1, 2] or ids == [2, 1], f"Expected IDs [1, 2] or [2, 1], got {ids}"


def test_single_process_add_remains_unchanged(tmp_path: Path) -> None:
    """Verify that single-process operation remains unchanged after the fix."""
    db = tmp_path / "single.json"
    app = TodoApp(db_path=str(db))

    # Add todos sequentially
    t1 = app.add("first")
    t2 = app.add("second")
    t3 = app.add("third")

    # IDs should be sequential
    assert t1.id == 1
    assert t2.id == 2
    assert t3.id == 3

    # Verify storage
    todos = app.list()
    assert len(todos) == 3
    assert [t.id for t in todos] == [1, 2, 3]
