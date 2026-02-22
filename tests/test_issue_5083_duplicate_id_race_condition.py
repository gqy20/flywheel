"""Regression test for issue #5083: next_id may produce duplicate IDs.

This test verifies that concurrent add operations do not produce duplicate IDs.
The issue is that next_id() and save() are not atomic - between calling next_id()
and save(), another process can call next_id() and get the same ID.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add() operations produce unique IDs.

    This is the failing regression test for issue #5083.
    When multiple processes add todos concurrently, they should not
    produce duplicate IDs.
    """
    db = tmp_path / "concurrent_add.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports the assigned ID."""
        try:
            app = TodoApp(db_path=str(db))
            todo = app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all workers at approximately the same time
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Check that all IDs are unique (this is the key assertion for issue #5083)
    assigned_ids = [r[2] for r in successes]
    unique_ids = set(assigned_ids)

    # With the bug, multiple workers may get the same ID (e.g., all get ID 1)
    # The fix should ensure all IDs are unique
    assert len(unique_ids) == num_workers, (
        f"Duplicate IDs detected! Got IDs: {sorted(assigned_ids)}, "
        f"unique: {sorted(unique_ids)}. "
        f"Each concurrent add should produce a unique ID."
    )


def test_next_id_returns_consistent_values():
    """Test basic next_id behavior on a single process."""
    storage = TodoStorage()
    from flywheel.todo import Todo

    # Empty list should return 1
    assert storage.next_id([]) == 1

    # List with id=1 should return 2
    todos = [Todo(id=1, text="first")]
    assert storage.next_id(todos) == 2

    # List with gaps should return max + 1
    todos = [Todo(id=1, text="first"), Todo(id=5, text="fifth")]
    assert storage.next_id(todos) == 6


def test_add_with_file_locking_produces_unique_ids(tmp_path: Path) -> None:
    """Test that the fixed add() with file locking produces unique IDs.

    This test uses more aggressive concurrency to stress-test the fix.
    """
    db = tmp_path / "stress_test.json"

    def add_worker(worker_id: int, count: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds multiple todos and reports all assigned IDs."""
        try:
            app = TodoApp(db_path=str(db))
            ids = []
            for i in range(count):
                todo = app.add(f"worker-{worker_id}-task-{i}")
                ids.append(todo.id)
            result_queue.put(("success", worker_id, ids))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # More workers, each adding multiple items
    num_workers = 3
    items_per_worker = 3
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, items_per_worker, result_queue))
        processes.append(p)
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=30)

    # Collect all IDs
    all_ids = []
    while not result_queue.empty():
        result = result_queue.get()
        if result[0] == "success":
            all_ids.extend(result[2])

    # All IDs should be unique
    assert len(all_ids) == len(set(all_ids)), (
        f"Duplicate IDs in stress test! Got: {sorted(all_ids)}"
    )
