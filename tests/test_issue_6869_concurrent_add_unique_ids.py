"""Regression test for issue #6869: Race condition in next_id() causing duplicate IDs.

This test verifies that concurrent add() operations from multiple processes
produce unique todo IDs, not duplicate IDs.

The race condition occurs because:
1. Process A loads todos (e.g., IDs [1, 2])
2. Process B loads todos (same IDs [1, 2])
3. Process A computes next_id = 3, adds todo, saves
4. Process B computes next_id = 3 (stale data), adds todo, saves
5. Result: Two todos with ID 3

The fix ensures that when saving, if a conflict is detected, the ID is
recomputed based on the current file state.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker that adds a todo and reports the assigned ID."""
    try:
        app = TodoApp(db_path=db_path)
        todo = app.add(f"worker-{worker_id} task")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add() operations produce unique IDs.

    This is a regression test for issue #6869. Multiple processes
    adding todos concurrently should never receive duplicate IDs.
    """
    db_path = str(tmp_path / "concurrent.json")

    # Start with one todo to establish baseline
    app = TodoApp(db_path=db_path)
    app.add("initial todo")

    num_workers = 10
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Launch all workers approximately simultaneously
    for i in range(num_workers):
        p = multiprocessing.Process(target=_add_todo_worker, args=(i, db_path, result_queue))
        processes.append(p)

    # Start all processes as close together as possible
    for p in processes:
        p.start()

    # Wait for all to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # All workers should succeed
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Extract IDs from successful results
    ids = [r[2] for r in successes]

    # CRITICAL: All IDs must be unique
    unique_ids = set(ids)
    assert len(unique_ids) == len(ids), (
        f"Duplicate IDs detected! Got IDs: {sorted(ids)}, "
        f"unique: {sorted(unique_ids)}. "
        f"Duplicates: {[id for id in ids if ids.count(id) > 1]}"
    )

    # Verify final file state has all todos with unique IDs
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # Should have initial + num_workers todos
    assert len(final_todos) == num_workers + 1, (
        f"Expected {num_workers + 1} todos, got {len(final_todos)}. "
        "Some todos may have been lost due to race condition."
    )

    # All final IDs must be unique
    final_ids = [todo.id for todo in final_todos]
    assert len(set(final_ids)) == len(final_ids), (
        f"Duplicate IDs in final file! IDs: {sorted(final_ids)}"
    )


def test_concurrent_add_preserves_all_todos(tmp_path: Path) -> None:
    """Test that concurrent adds don't lose data.

    Even with the race condition, the last-writer-wins behavior of atomic
    saves should not cause data loss when ID conflict resolution is used.
    """
    db_path = str(tmp_path / "preserve.json")

    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=_add_todo_worker, args=(i, db_path, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Verify all todos are present in final file
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # Each worker added one todo, all should be present
    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos, got {len(final_todos)}. "
        "Data was lost during concurrent writes."
    )

    # Verify all worker texts are present
    texts = {todo.text for todo in final_todos}
    for i in range(num_workers):
        expected_text = f"worker-{i} task"
        assert expected_text in texts, f"Missing todo from worker {i}: {expected_text}"


def test_single_process_sequential_add_unique_ids(tmp_path: Path) -> None:
    """Baseline test: single process sequential adds should always work."""
    db_path = str(tmp_path / "sequential.json")
    app = TodoApp(db_path=db_path)

    ids = []
    for i in range(10):
        todo = app.add(f"task {i}")
        ids.append(todo.id)

    # All IDs should be unique and sequential
    assert len(set(ids)) == len(ids), f"Duplicate IDs in sequential adds: {ids}"
    assert ids == sorted(ids), f"IDs not sequential: {ids}"
