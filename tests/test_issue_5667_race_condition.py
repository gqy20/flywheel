"""Tests for issue #5667: Race condition in add operation.

This test suite verifies that concurrent add() operations:
1. Do not produce duplicate IDs
2. Do not lose any todo items
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _add_worker(worker_id: int, db_path: str, num_adds: int, result_queue: multiprocessing.Queue) -> None:
    """Worker function that adds multiple todos concurrently."""
    try:
        app = TodoApp(db_path=db_path)
        added_ids = []
        for i in range(num_adds):
            todo = app.add(f"worker-{worker_id}-todo-{i}")
            added_ids.append(todo.id)
        result_queue.put(("success", worker_id, added_ids))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_operations_no_duplicate_ids(tmp_path: Path) -> None:
    """Regression test for issue #5667: Concurrent adds must not produce duplicate IDs.

    This test spawns multiple processes that each add todos to the same file.
    After completion, all IDs in the file must be unique.
    """
    db_path = str(tmp_path / "concurrent.json")

    # Run multiple workers concurrently, each adding multiple todos
    num_workers = 4
    num_adds_per_worker = 25  # Total 100 todos
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=_add_worker,
            args=(worker_id, db_path, num_adds_per_worker, result_queue)
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

    # Verify all workers succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Load final state and verify no duplicate IDs
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    all_ids = [todo.id for todo in final_todos]
    unique_ids = set(all_ids)

    # Key assertion: No duplicate IDs allowed
    assert len(all_ids) == len(unique_ids), (
        f"Duplicate IDs detected! "
        f"Total IDs: {len(all_ids)}, Unique IDs: {len(unique_ids)}. "
        f"Duplicates: {[id_ for id_ in all_ids if all_ids.count(id_) > 1]}"
    )


def test_concurrent_add_operations_no_lost_updates(tmp_path: Path) -> None:
    """Regression test for issue #5667: Concurrent adds must not lose any todos.

    This test verifies that all todos added by concurrent processes are
    present in the final file (no lost updates due to last-writer-wins).
    """
    db_path = str(tmp_path / "concurrent.json")

    # Run multiple workers concurrently
    num_workers = 4
    num_adds_per_worker = 25  # Total expected: 100 todos
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=_add_worker,
            args=(worker_id, db_path, num_adds_per_worker, result_queue)
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

    # Verify all workers succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers

    # Load final state
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # Key assertion: All todos must be present
    expected_total = num_workers * num_adds_per_worker
    assert len(final_todos) == expected_total, (
        f"Lost updates detected! "
        f"Expected {expected_total} todos, but only {len(final_todos)} exist. "
        f"Lost {expected_total - len(final_todos)} todos."
    )


def test_concurrent_add_with_preexisting_todos(tmp_path: Path) -> None:
    """Test that concurrent adds work correctly when there are pre-existing todos."""
    db_path = str(tmp_path / "concurrent.json")

    # Create initial todos
    app = TodoApp(db_path=db_path)
    app.add("pre-existing-1")
    app.add("pre-existing-2")

    # Now run concurrent adds
    num_workers = 2
    num_adds_per_worker = 10
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=_add_worker,
            args=(worker_id + 10, db_path, num_adds_per_worker, result_queue)
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers

    # Verify final state
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # Should have 2 pre-existing + 20 new = 22 total
    expected_total = 2 + (num_workers * num_adds_per_worker)
    assert len(final_todos) == expected_total, (
        f"Expected {expected_total} todos, got {len(final_todos)}"
    )

    # All IDs should be unique
    all_ids = [todo.id for todo in final_todos]
    assert len(all_ids) == len(set(all_ids)), "Duplicate IDs detected"

    # Pre-existing todos should still be present
    texts = [todo.text for todo in final_todos]
    assert "pre-existing-1" in texts
    assert "pre-existing-2" in texts
