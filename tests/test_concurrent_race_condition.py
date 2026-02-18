"""Tests for race condition in load-modify-save pattern (Issue #4355).

This test suite verifies that concurrent load-modify-save operations
do not result in data loss. The race condition occurs when:
1. Process A loads todos
2. Process B loads todos (same state as A)
3. Process A modifies and saves
4. Process B modifies and saves (overwrites A's changes)

The fix should ensure read-modify-write atomicity via file locking.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_operations_lose_data(tmp_path: Path) -> None:
    """Regression test for issue #4355: Race condition in load-modify-save.

    Tests that when two processes simultaneously call add():
    - Each process loads the current todos
    - Each process calculates next_id based on loaded todos
    - Each process saves its modified list

    Without locking, the second save overwrites the first, causing data loss.
    With proper locking, both todos should be preserved.
    """
    db_path = tmp_path / "race_test.json"

    def add_todo_worker(worker_id: int, db_path_str: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo using TodoApp.add() which does load-modify-save."""
        try:
            app = TodoApp(db_path=db_path_str)
            # Small stagger to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))

            # This add() does: load() -> next_id() -> save()
            todo = app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers that all try to add todos concurrently
    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=add_todo_worker,
            args=(i, str(db_path), result_queue)
        )
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should succeed
    assert len(errors) == 0, f"Workers had errors: {errors}"
    assert len(successes) == num_workers

    # CRITICAL: Verify that ALL todos were preserved
    # Without locking, we would lose data (last-writer-wins on load-modify-save)
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()

    # All workers should have their todo preserved
    # This is the key assertion - without proper locking, some todos would be lost
    assert len(final_todos) == num_workers, (
        f"Data loss detected! Expected {num_workers} todos, got {len(final_todos)}. "
        f"Results: {successes}. This indicates load-modify-save race condition."
    )

    # Verify all worker tasks are present
    texts = {todo.text for todo in final_todos}
    for i in range(num_workers):
        expected_text = f"worker-{i}-task"
        assert expected_text in texts, f"Missing {expected_text} - data was lost due to race condition"


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent adds produce unique IDs (no ID collision).

    When processes load the same state and calculate next_id independently,
    they may assign duplicate IDs, causing ambiguity.
    """
    db_path = tmp_path / "id_collision_test.json"

    def add_todo_worker(worker_id: int, db_path_str: str, result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path=db_path_str)
            time.sleep(0.002 * (worker_id % 4))
            todo = app.add(f"task-{worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=add_todo_worker,
            args=(i, str(db_path), result_queue)
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers

    # Verify all IDs are unique
    ids = [r[2] for r in successes]
    assert len(ids) == len(set(ids)), (
        f"ID collision detected! IDs: {ids}. "
        f"Multiple processes assigned the same ID due to race condition."
    )


def test_file_locking_prevents_race_condition(tmp_path: Path) -> None:
    """Test that file locking prevents the load-modify-save race condition.

    This test verifies that when using the locked_modify method,
    concurrent operations are properly serialized and no data is lost.
    """
    db_path = tmp_path / "locked_test.json"

    def locked_add_worker(worker_id: int, db_path_str: str, result_queue: multiprocessing.Queue) -> None:
        try:
            storage = TodoStorage(db_path_str)
            time.sleep(0.001 * (worker_id % 3))

            # Use the atomic modify operation if available
            # This should acquire a lock, load, modify, and save atomically
            def add_todo(todos: list) -> list:
                from flywheel.todo import Todo
                next_id = max((t.id for t in todos), default=0) + 1 if todos else 1
                new_list = list(todos)  # Copy
                new_list.append(Todo(id=next_id, text=f"locked-worker-{worker_id}"))
                return new_list

            storage.modify_atomically(add_todo)
            result_queue.put(("success", worker_id, None))
        except AttributeError:
            # If modify_atomically doesn't exist yet, skip this test gracefully
            result_queue.put(("skip", worker_id, "modify_atomically not implemented"))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 5
    processes = []
    result_queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=locked_add_worker,
            args=(i, str(db_path), result_queue)
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    skips = [r for r in results if r[0] == "skip"]
    if skips:
        pytest.skip("modify_atomically not yet implemented")

    errors = [r for r in results if r[0] == "error"]
    successes = [r for r in results if r[0] == "success"]

    assert len(errors) == 0, f"Workers had errors: {errors}"
    assert len(successes) == num_workers

    # All todos should be preserved
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()

    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos with locking, got {len(final_todos)}"
    )
