"""Regression test for issue #4859: Race condition in next_id() when used concurrently.

This test suite verifies that concurrent add() operations produce unique IDs,
preventing the race condition where multiple processes may get the same ID.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #4859: Concurrent add() should produce unique IDs.

    When multiple processes call add() concurrently on the same database file,
    each todo should receive a unique ID. Without proper synchronization, the
    next_id() function can return the same value to multiple processes, causing
    ID collisions.

    The fix uses file locking (fcntl.flock) to ensure that the entire
    load-compute_id-save sequence is atomic.
    """
    db = tmp_path / "concurrent_todos.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds a todo and reports the assigned ID."""
        try:
            app = TodoApp(db_path=str(db))
            # Each worker adds a unique todo
            todo = app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
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

    # Print errors for debugging if any failed
    if errors:
        for err in errors:
            print(f"Worker {err[1]} error: {err[2]}")

    assert len(errors) == 0, f"Some workers failed: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Critical assertion: all IDs should be unique
    ids_assigned = [r[2] for r in successes]
    unique_ids = set(ids_assigned)

    assert len(unique_ids) == len(ids_assigned), (
        f"ID collision detected! {len(ids_assigned)} todos were created but only "
        f"{len(unique_ids)} unique IDs were assigned. "
        f"IDs assigned: {sorted(ids_assigned)}"
    )

    # Verify final state: load all todos and check uniqueness
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # All todos should have unique IDs in the final file
    final_ids = [todo.id for todo in final_todos]
    assert len(set(final_ids)) == len(final_ids), (
        f"Duplicate IDs found in final file! IDs: {sorted(final_ids)}"
    )

    # Verify all expected todos are present
    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos, found {len(final_todos)}"
    )


def test_concurrent_add_maintains_data_integrity(tmp_path: Path) -> None:
    """Verify that concurrent adds don't cause data loss or corruption.

    Even with the race condition fix, we should verify that:
    1. All added todos are present in the final file
    2. Each todo's data is intact (correct text)
    3. No partial or corrupted data exists
    """
    db = tmp_path / "integrity_test.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a uniquely identifiable todo."""
        try:
            app = TodoApp(db_path=str(db))
            unique_text = f"worker-{worker_id:03d}-unique-marker-xyz"
            todo = app.add(unique_text)
            result_queue.put(("success", worker_id, todo.id, unique_text))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
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
    assert len(successes) == num_workers

    # Verify all expected texts are present
    storage = TodoStorage(str(db))
    final_todos = storage.load()
    final_texts = {todo.text for todo in final_todos}

    for success in successes:
        expected_text = success[3]
        assert expected_text in final_texts, (
            f"Missing todo with text '{expected_text}'. Present texts: {final_texts}"
        )
