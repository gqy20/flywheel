"""Regression test for issue #2928: Race condition in concurrent ID generation.

This test verifies that when multiple processes add todos concurrently,
each gets a unique ID and no data is lost.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def worker_add_todos(
    db_path: str, worker_id: int, num_adds: int, result_queue: multiprocessing.Queue
) -> None:
    """Worker that adds multiple todos and reports results."""
    try:
        app = TodoApp(db_path=db_path)
        added_ids = []
        for i in range(num_adds):
            todo = app.add(f"worker-{worker_id}-task-{i}")
            added_ids.append(todo.id)
        result_queue.put(("success", worker_id, added_ids))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #2928.

    Multiple processes adding todos concurrently should produce unique IDs
    and preserve all data (no lost writes).
    """
    db_path = str(tmp_path / "concurrent.json")

    num_workers = 5
    adds_per_worker = 10
    expected_total = num_workers * adds_per_worker

    # Spawn workers that each add todos concurrently
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    for worker_id in range(num_workers):
        p = multiprocessing.Process(
            target=worker_add_todos,
            args=(db_path, worker_id, adds_per_worker, result_queue),
        )
        processes.append(p)
        p.start()

    # Wait for all workers to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Verify no errors occurred
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers, (
        f"Expected {num_workers} successes, got {len(successes)}"
    )

    # Collect all IDs that were assigned
    all_ids = []
    for success in successes:
        _, worker_id, ids = success
        all_ids.extend(ids)

    # Load final state from storage
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # Verify exact count - all writes should be preserved
    assert len(final_todos) == expected_total, (
        f"Expected {expected_total} todos, got {len(final_todos)}. "
        f"This indicates lost writes due to race condition."
    )

    # Verify all IDs are unique
    final_ids = [todo.id for todo in final_todos]
    unique_ids = set(final_ids)
    assert len(unique_ids) == len(final_ids), (
        f"ID collision detected! {len(final_ids)} todos but only {len(unique_ids)} "
        f"unique IDs. Duplicate IDs: {[i for i in final_ids if final_ids.count(i) > 1]}"
    )

    # Verify IDs form a contiguous sequence starting from 1
    expected_ids = set(range(1, expected_total + 1))
    assert unique_ids == expected_ids, (
        f"IDs should form contiguous sequence 1..{expected_total}. "
        f"Got: {sorted(unique_ids)}"
    )


def test_single_process_add_still_works(tmp_path: Path) -> None:
    """Verify single-process behavior is unchanged after fix."""
    db_path = str(tmp_path / "single.json")
    app = TodoApp(db_path=db_path)

    # Add several todos in sequence
    todos = []
    for i in range(5):
        todo = app.add(f"task-{i}")
        todos.append(todo)

    # Verify IDs are sequential
    ids = [t.id for t in todos]
    assert ids == [1, 2, 3, 4, 5]

    # Verify all can be listed
    all_todos = app.list()
    assert len(all_todos) == 5

    # Verify content matches
    for i, todo in enumerate(all_todos):
        assert todo.text == f"task-{i}"
