"""Regression test for issue #5241: next_id() race condition in concurrent scenarios.

This test verifies that concurrent add() operations produce unique IDs
and don't result in duplicate IDs or data corruption.

The issue: next_id() was computed from the loaded list without any locking,
so two processes loading at the same time would compute the same next_id.

The fix: Use file locking to protect the load-compute-save operation as an
atomic unit in the add() method.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.cli import TodoApp


def _add_todo_worker(
    db_path: str,
    text_prefix: str,
    worker_id: int,
    result_queue: multiprocessing.Queue,
) -> None:
    """Worker function that adds a todo and reports the assigned ID."""
    try:
        app = TodoApp(db_path=db_path)
        todo = app.add(f"{text_prefix}-worker-{worker_id}")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for #5241: Concurrent add() should produce unique IDs.

    The test spawns multiple processes that each add a todo concurrently.
    All todos should receive unique IDs.
    """
    db_path = str(tmp_path / "concurrent_test.json")

    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Spawn workers that will add todos concurrently
    for i in range(num_workers):
        p = multiprocessing.Process(
            target=_add_todo_worker,
            args=(db_path, "test", i, result_queue),
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

    # All workers should have succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Extract all IDs from successful results
    ids = [r[2] for r in successes]

    # All IDs must be unique - this is the core assertion for #5241
    assert len(ids) == len(set(ids)), f"Duplicate IDs detected: {ids}"

    # Verify final state via load - should have exactly num_workers todos
    app = TodoApp(db_path=db_path)
    todos = app.list()
    assert len(todos) == num_workers, f"Expected {num_workers} todos, got {len(todos)}"

    # Verify all loaded IDs are also unique
    loaded_ids = [t.id for t in todos]
    assert len(loaded_ids) == len(set(loaded_ids)), f"Duplicate IDs in loaded data: {loaded_ids}"


def test_concurrent_add_preserves_data_integrity(tmp_path: Path) -> None:
    """Verify that concurrent add() operations don't corrupt the JSON file.

    After multiple concurrent adds, the file should be valid JSON and
    contain exactly the expected number of todos.
    """
    db_path = str(tmp_path / "integrity_test.json")

    num_workers = 10
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all workers as close together as possible
    for i in range(num_workers):
        p = multiprocessing.Process(
            target=_add_todo_worker,
            args=(db_path, "integrity", i, result_queue),
        )
        processes.append(p)

    # Start all processes nearly simultaneously
    for p in processes:
        p.start()

    # Wait for all to complete
    for p in processes:
        p.join(timeout=30)

    # The file should be valid and loadable
    app = TodoApp(db_path=db_path)
    todos = app.list()

    # Verify we have exactly num_workers todos
    assert len(todos) == num_workers

    # Verify all todos have unique IDs
    ids = [t.id for t in todos]
    assert len(ids) == len(set(ids))


def test_sequential_add_produces_sequential_ids(tmp_path: Path) -> None:
    """Baseline test: Sequential add() should produce sequential IDs 1, 2, 3..."""
    db_path = str(tmp_path / "sequential_test.json")
    app = TodoApp(db_path=db_path)

    ids = []
    for i in range(5):
        todo = app.add(f"todo-{i}")
        ids.append(todo.id)

    # IDs should be sequential starting from 1
    assert ids == [1, 2, 3, 4, 5]
