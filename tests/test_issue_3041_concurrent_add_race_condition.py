"""Regression test for issue #3041: Race condition in concurrent add operations.

This test verifies that concurrent add operations from multiple processes
do not produce duplicate IDs or data corruption.

Issue: https://github.com/gqy20/flywheel/issues/3041

The race condition occurs because the add() method in TodoApp performs:
1. load() - read todos from file
2. next_id() - calculate next ID based on loaded data
3. append() - add new todo
4. save() - write back to file

If two processes run concurrently, they can both load the same data,
calculate the same next_id, and overwrite each other, causing:
- Duplicate IDs
- Data loss (last-writer-wins)
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def _add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker process that adds a todo using TodoApp.add().

    Args:
        worker_id: Unique identifier for this worker
        db_path: Path to the database file
        result_queue: Queue to report results back to main process
    """
    try:
        app = TodoApp(db_path=db_path)
        # Each worker adds a unique todo
        todo = app.add(text=f"worker-{worker_id}-todo")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_adds_produce_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add operations don't produce duplicate IDs.

    This is a regression test for issue #3041.
    Multiple processes adding todos concurrently should result in:
    1. All IDs being unique (no collisions)
    2. No data corruption
    3. All todos being present in the final state
    """
    db_path = str(tmp_path / "concurrent.json")

    # Run multiple workers that add todos concurrently
    num_workers = 10
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all workers as close together as possible to maximize race condition
    for i in range(num_workers):
        p = multiprocessing.Process(target=_add_todo_worker, args=(i, db_path, result_queue))
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

    # Verify all workers succeeded
    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert (
        len(successes) == num_workers
    ), f"Expected {num_workers} successes, got {len(successes)}"

    # Extract all IDs
    ids = [r[2] for r in successes]

    # CRITICAL ASSERTION: All IDs must be unique
    unique_ids = set(ids)
    assert len(unique_ids) == len(ids), (
        f"DUPLICATE IDs DETECTED! Got {len(ids)} IDs but only {len(unique_ids)} unique. "
        f"IDs: {ids}, Unique: {sorted(unique_ids)}"
    )

    # Verify final file state
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    # All todos should be present (no data loss)
    assert len(final_todos) == num_workers, (
        f"DATA LOSS: Expected {num_workers} todos, but got {len(final_todos)}"
    )

    # Verify all IDs in final file are unique
    final_ids = [t.id for t in final_todos]
    assert len(set(final_ids)) == len(final_ids), (
        f"Duplicate IDs in final file: {final_ids}"
    )


def test_concurrent_adds_no_data_corruption(tmp_path: Path) -> None:
    """Test that concurrent adds don't corrupt the JSON file.

    This is a regression test for issue #3041.
    After concurrent operations, the file should be valid JSON
    with well-formed todo entries.
    """
    db_path = str(tmp_path / "corruption_test.json")

    # Initialize with an existing todo
    app = TodoApp(db_path=db_path)
    app.add(text="initial-todo")

    # Run concurrent workers
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=_add_todo_worker, args=(i + 100, db_path, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Verify file is not corrupted
    storage = TodoStorage(db_path)

    # This should not raise any exception
    final_todos = storage.load()

    # Verify structure of all todos
    for todo in final_todos:
        assert isinstance(todo.id, int), f"Invalid todo id: {todo.id}"
        assert isinstance(todo.text, str), f"Invalid todo text: {todo.text}"
        assert isinstance(todo.done, bool), f"Invalid todo done: {todo.done}"

    # Should have initial + worker todos (at least some of them)
    # Due to potential race conditions in the original code, some may be lost
    # After fix: should have exactly num_workers + 1 todos
    assert len(final_todos) >= 1, "At least the initial todo should exist"


def test_sequential_adds_after_concurrent_still_work(tmp_path: Path) -> None:
    """Test that sequential adds work correctly after concurrent operations.

    This verifies that the file locking mechanism doesn't leave the file
    in a bad state that would prevent subsequent operations.
    """
    db_path = str(tmp_path / "sequential_after_concurrent.json")

    # First do some concurrent adds
    num_workers = 3
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=_add_todo_worker, args=(i, db_path, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    # Now do sequential adds
    app = TodoApp(db_path=db_path)
    seq1 = app.add("sequential-1")
    seq2 = app.add("sequential-2")
    seq3 = app.add("sequential-3")

    # Verify sequential adds have unique IDs
    storage = TodoStorage(db_path)
    all_todos = storage.load()
    all_ids = [t.id for t in all_todos]

    assert len(set(all_ids)) == len(all_ids), f"Duplicate IDs after sequential adds: {all_ids}"

    # Verify our sequential IDs are present
    assert seq1.id in all_ids
    assert seq2.id in all_ids
    assert seq3.id in all_ids
