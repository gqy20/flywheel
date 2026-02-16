"""Regression test for issue #3577: Duplicate ID generation in concurrent writes.

This test verifies that concurrent add operations do not produce duplicate IDs
when multiple processes are adding todos to the same database file.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add operations produce unique IDs.

    This is a regression test for issue #3577 where next_id() computes
    new ID based on current max ID without any locking mechanism,
    which can cause duplicate IDs under concurrent access.
    """
    import time

    db = tmp_path / "concurrent_ids.json"

    # Number of todos each worker adds
    num_todos_per_worker = 5
    # Number of concurrent workers
    num_workers = 5

    def add_todos_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        """Worker function that adds multiple todos and reports their IDs."""
        try:
            app = TodoApp(db_path=db_path)
            added_ids = []
            for i in range(num_todos_per_worker):
                todo = app.add(f"worker-{worker_id}-todo-{i}")
                added_ids.append(todo.id)
                # Small delay to increase race condition likelihood
                time.sleep(0.001)
            result_queue.put(("success", worker_id, added_ids))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=add_todos_worker,
            args=(i, str(db), result_queue)
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
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Collect all IDs that were generated
    all_ids = []
    successes = [r for r in results if r[0] == "success"]
    for success in successes:
        _, _worker_id, added_ids = success
        all_ids.extend(added_ids)

    # The key assertion: all IDs should be unique
    # Without proper locking, multiple workers may compute the same next_id
    # based on the same "current max" value
    unique_ids = set(all_ids)
    assert len(unique_ids) == len(all_ids), (
        f"Duplicate IDs detected! "
        f"Generated {len(all_ids)} IDs but only {len(unique_ids)} are unique. "
        f"Duplicates: {[i for i in all_ids if all_ids.count(i) > 1]}"
    )

    # Also verify the final file has no duplicate IDs
    storage = TodoStorage(str(db))
    final_todos = storage.load()
    final_ids = [todo.id for todo in final_todos]
    unique_final_ids = set(final_ids)
    assert len(unique_final_ids) == len(final_ids), (
        f"Final database contains duplicate IDs! "
        f"Duplicates: {[i for i in final_ids if final_ids.count(i) > 1]}"
    )


def test_next_id_race_condition_revealed(tmp_path: Path) -> None:
    """Test that exposes the race condition in next_id().

    This test verifies that using atomic_access() prevents race conditions
    when manually loading, computing next_id, and saving.
    """
    db = tmp_path / "race_ids.json"

    # Initialize with one todo
    storage = TodoStorage(str(db))
    storage.save([Todo(id=1, text="initial")])

    num_workers = 5

    def race_next_id_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that uses atomic_access to safely add a todo."""
        try:
            # Each worker uses atomic_access for safe concurrent access
            local_storage = TodoStorage(db_path)
            with local_storage.atomic_access() as todos:
                new_id = local_storage.next_id(todos)
                new_todo = Todo(id=new_id, text=f"worker-{worker_id}")
                todos.append(new_todo)
            result_queue.put(("success", worker_id, new_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Start all workers at approximately the same time
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Use a barrier to synchronize start
    barrier = multiprocessing.Barrier(num_workers)

    def synchronized_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        barrier.wait()  # Wait for all workers to be ready
        race_next_id_worker(worker_id, db_path, result_queue)

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=synchronized_worker,
            args=(i, str(db), result_queue)
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

    # Collect all IDs that were generated
    all_ids = []
    for r in results:
        if r[0] == "success":
            all_ids.append(r[2])

    # With atomic_access locking, all IDs should be unique
    unique_ids = set(all_ids)
    if len(unique_ids) != len(all_ids):
        duplicates = [i for i in all_ids if all_ids.count(i) > 1]
        pytest.fail(
            f"Race condition detected: {len(all_ids) - len(unique_ids)} "
            f"duplicate IDs generated. Duplicates: {set(duplicates)}"
        )
