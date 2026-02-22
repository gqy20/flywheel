"""Regression test for issue #5113: Race condition in add() - duplicate IDs.

This test verifies that concurrent add() operations from multiple processes
do not produce duplicate IDs. The race condition occurs because:
1. Process A loads todos, computes next_id=2
2. Process B loads todos, computes next_id=2 (before A saves)
3. Both processes save todos with id=2, causing duplicates

The fix uses file locking to ensure atomicity of the add operation.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def add_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker that adds a todo using TodoApp.add()."""
    try:
        app = TodoApp(db_path=db_path)
        # Small stagger to increase race condition likelihood
        time.sleep(0.001 * (worker_id % 3))
        todo = app.add(f"worker-{worker_id}-todo")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_no_duplicate_ids(tmp_path: Path) -> None:
    """Test that concurrent add() operations produce unique IDs.

    This is the regression test for issue #5113. Multiple processes
    calling add() concurrently should never produce duplicate IDs.
    """
    db_path = str(tmp_path / "test.json")

    # Create initial todo so next_id isn't always 1
    app = TodoApp(db_path=db_path)
    app.add("initial todo")

    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all workers nearly simultaneously
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, db_path, result_queue))
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

    # Verify all IDs are unique - this is the key assertion
    ids_returned = [r[2] for r in successes]
    unique_ids = set(ids_returned)

    assert len(unique_ids) == len(ids_returned), (
        f"Duplicate IDs detected! Got IDs: {sorted(ids_returned)}, "
        f"unique: {sorted(unique_ids)}, "
        f"duplicates: {[id for id in ids_returned if ids_returned.count(id) > 1]}"
    )

    # Also verify the stored todos have unique IDs
    storage = TodoStorage(db_path)
    stored_todos = storage.load()
    stored_ids = [t.id for t in stored_todos]
    unique_stored_ids = set(stored_ids)

    # Note: Due to race conditions, some todos may be lost (last-writer-wins)
    # But all stored IDs must be unique
    assert len(unique_stored_ids) == len(stored_ids), (
        f"Stored todos have duplicate IDs! IDs: {sorted(stored_ids)}"
    )


def test_concurrent_add_preserves_all_todos_with_locking(tmp_path: Path) -> None:
    """Test that file locking allows all concurrent adds to complete.

    With proper file locking, all concurrent add() operations should
    succeed and all todos should be preserved in storage.
    """
    db_path = str(tmp_path / "test2.json")

    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all workers nearly simultaneously
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, db_path, result_queue))
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
    assert len(successes) == num_workers, f"Expected {num_workers} successes"

    # With locking, all todos should be preserved
    storage = TodoStorage(db_path)
    stored_todos = storage.load()

    # All 5 workers should have added their todos
    assert len(stored_todos) == num_workers, (
        f"Expected {num_workers} todos, got {len(stored_todos)}. "
        f"Some todos were lost due to race condition."
    )

    # All stored IDs must be unique
    stored_ids = [t.id for t in stored_todos]
    assert len(set(stored_ids)) == len(stored_ids), (
        f"Stored todos have duplicate IDs: {stored_ids}"
    )
