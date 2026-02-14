"""Regression test for issue #3392: Race condition in next_id() causing ID collisions.

This test verifies that concurrent add operations do not result in duplicate IDs.
The race condition occurs when multiple processes read the same todos list,
calculate the same next_id, and save with duplicate IDs.

Fix approach: Use file locking (flock) to ensure atomicity of the load-compute-save cycle.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_no_duplicate_ids(tmp_path: Path) -> None:
    """Regression test for issue #3392: Concurrent add operations should not create duplicate IDs.

    This test spawns multiple processes that all try to add todos concurrently.
    Without proper synchronization, they will:
    1. Read the same empty file
    2. All calculate next_id = 1
    3. All save with id=1, overwriting each other

    With the fix, each process should get a unique ID through file locking.
    """
    db = tmp_path / "race_test.json"
    num_processes = 10

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo and reports the assigned ID."""
        try:
            app = TodoApp(str(db))
            # Small random-ish delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 5))
            todo = app.add(f"task from worker {worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Start all workers at roughly the same time
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_processes):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Check for errors
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify we got the expected number of results
    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_processes, f"Expected {num_processes} successes, got {len(successes)}"

    # Get the IDs that were assigned
    assigned_ids = [r[2] for r in successes]

    # The key assertion: all IDs should be unique (no duplicates)
    unique_ids = set(assigned_ids)
    assert len(unique_ids) == len(
        assigned_ids
    ), f"Duplicate IDs detected! Assigned IDs: {sorted(assigned_ids)}, Unique: {sorted(unique_ids)}"


def test_concurrent_add_all_todos_persisted(tmp_path: Path) -> None:
    """After concurrent adds, all todos should be present in the final file.

    This verifies not only unique IDs but also that no data is lost
    due to race conditions in the save operation.
    """
    db = tmp_path / "persist_test.json"
    num_processes = 5

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a unique todo."""
        try:
            app = TodoApp(str(db))
            # Use unique text so we can verify presence
            unique_text = f"unique-task-{worker_id}-marker"
            app.add(unique_text)
            result_queue.put(("success", worker_id, unique_text))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Start all workers
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_processes):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=30)

    # Collect what was supposed to be added
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    added_texts = {r[2] for r in successes}

    # Load final state
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # Check all expected todos are present and have unique IDs
    final_texts = {todo.text for todo in final_todos}
    assert final_texts == added_texts, (
        f"Not all todos persisted. Expected: {added_texts}, Got: {final_texts}"
    )
    assert len(final_todos) > 0, "No todos were persisted"
    assert len(final_todos) == len({todo.id for todo in final_todos}), "Duplicate IDs in final file"


def test_single_process_add_still_works(tmp_path: Path) -> None:
    """Verify single-process behavior is not broken by the fix."""
    app = TodoApp(str(tmp_path / "single.json"))

    # Add multiple todos sequentially
    todo1 = app.add("first")
    todo2 = app.add("second")
    todo3 = app.add("third")

    # IDs should be sequential
    assert todo1.id == 1
    assert todo2.id == 2
    assert todo3.id == 3

    # All should be present
    todos = app.list()
    assert len(todos) == 3
    assert todos[0].text == "first"
    assert todos[1].text == "second"
    assert todos[2].text == "third"
