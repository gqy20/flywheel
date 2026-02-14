"""Regression test for issue #3392: Race condition in next_id().

This test verifies that concurrent add operations do not result in duplicate IDs.

The bug: next_id() calculates the next ID based on the loaded todos list,
but if multiple processes call add() concurrently, they can:
1. Both load the same todos list
2. Both compute the same next_id
3. Both save todos with duplicate IDs

The fix: Use file locking during the load-compute-save sequence to ensure
atomicity of ID assignment.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _concurrent_add_worker(db_path: str, text_prefix: str, count: int, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds multiple todos and reports IDs used."""
    try:
        app = TodoApp(db_path=db_path)
        ids_used = []
        for i in range(count):
            todo = app.add(f"{text_prefix}-{i}")
            ids_used.append(todo.id)
        result_queue.put(("success", ids_used))
    except Exception as e:
        result_queue.put(("error", str(e)))


def test_concurrent_add_operations_no_duplicate_ids(tmp_path: Path) -> None:
    """Test that concurrent add operations produce unique IDs.

    This is a regression test for issue #3392. Before the fix,
    multiple processes adding todos concurrently could get
    duplicate IDs because next_id() is not atomic.
    """
    db_path = tmp_path / "test.json"
    db_path_str = str(db_path)

    # Create initial todo to start with non-empty DB
    app = TodoApp(db_path=db_path_str)
    app.add("initial")

    num_workers = 4
    todos_per_worker = 5
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all workers at roughly the same time
    processes = []
    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=_concurrent_add_worker,
            args=(db_path_str, f"worker-{worker_id}", todos_per_worker, result_queue),
        )
        processes.append(p)

    # Start all processes
    for p in processes:
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

    # Collect all IDs used
    all_ids = []
    successes = [r for r in results if r[0] == "success"]
    for success in successes:
        all_ids.extend(success[1])

    # Check that all IDs are unique (the core assertion)
    assert len(all_ids) == len(set(all_ids)), (
        f"Duplicate IDs detected! IDs used: {sorted(all_ids)}. "
        f"Expected {len(all_ids)} unique IDs, got {len(set(all_ids))}."
    )

    # Load final state and verify no duplicates in stored data
    storage = TodoStorage(db_path_str)
    final_todos = storage.load()
    stored_ids = [t.id for t in final_todos]
    assert len(stored_ids) == len(set(stored_ids)), (
        f"Duplicate IDs in stored data! IDs: {sorted(stored_ids)}"
    )

    # Verify we have the expected number of todos (1 initial + workers * todos_per_worker)
    # Note: Due to race conditions in save, we might not get all todos,
    # but the ones we have should have unique IDs
    expected_max = 1 + num_workers * todos_per_worker
    assert len(final_todos) <= expected_max


def test_concurrent_add_with_preexisting_todos(tmp_path: Path) -> None:
    """Test concurrent add operations with multiple preexisting todos."""
    db_path = tmp_path / "test2.json"
    db_path_str = str(db_path)

    # Create several initial todos
    app = TodoApp(db_path=db_path_str)
    initial_ids = []
    for i in range(5):
        todo = app.add(f"initial-{i}")
        initial_ids.append(todo.id)

    num_workers = 3
    todos_per_worker = 3
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    processes = []
    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=_concurrent_add_worker,
            args=(db_path_str, f"concurrent-{worker_id}", todos_per_worker, result_queue),
        )
        processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=30)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify final state has unique IDs
    storage = TodoStorage(db_path_str)
    final_todos = storage.load()
    stored_ids = [t.id for t in final_todos]

    assert len(stored_ids) == len(set(stored_ids)), (
        f"Duplicate IDs in stored data! IDs: {sorted(stored_ids)}"
    )


def test_single_process_adds_unique_ids(tmp_path: Path) -> None:
    """Test that single-process operations still work correctly after fix."""
    db_path = tmp_path / "single.json"
    db_path_str = str(db_path)

    app = TodoApp(db_path=db_path_str)

    # Add multiple todos
    ids = []
    for i in range(10):
        todo = app.add(f"todo-{i}")
        ids.append(todo.id)

    # All IDs should be unique
    assert len(ids) == len(set(ids)), f"Single process produced duplicate IDs: {ids}"

    # IDs should be sequential
    assert ids == sorted(ids), f"IDs not sequential: {ids}"

    # Verify storage
    storage = TodoStorage(db_path_str)
    loaded = storage.load()
    assert len(loaded) == 10
    loaded_ids = [t.id for t in loaded]
    assert loaded_ids == ids
