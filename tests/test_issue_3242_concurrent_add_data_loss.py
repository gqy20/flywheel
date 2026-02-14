"""Regression test for issue #3242: Concurrent add() operations can cause data loss.

This test verifies that when multiple processes call TodoApp.add() concurrently,
all todos are properly persisted without data loss due to the non-atomic
load-modify-save pattern.

The bug: add() does load -> modify -> save as separate steps, so:
1. Process A loads [] (empty)
2. Process B loads [] (empty)
3. Process A adds todo, saves [todo_A]
4. Process B adds todo, saves [todo_B]  <-- Process A's todo is lost!

The fix: Use file locking to make load-modify-save atomic.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.todo import Todo


def _add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
    """Worker that adds a single todo via TodoApp.add()."""
    try:
        app = TodoApp(db_path=db_path)
        todo = app.add(f"worker-{worker_id}-todo")
        result_queue.put(("success", worker_id, todo.id))
    except Exception as e:
        result_queue.put(("error", worker_id, str(e)))


def test_concurrent_add_preserves_all_todos() -> None:
    """Test that concurrent add() operations don't lose data.

    This is a regression test for issue #3242.
    When multiple processes add todos concurrently, ALL todos should
    be present in the final state, not just the last writer's todos.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.json")

        num_workers = 10
        processes = []
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        # Start all workers concurrently
        for i in range(num_workers):
            p = multiprocessing.Process(target=_add_todo_worker, args=(i, db_path, result_queue))
            processes.append(p)

        # Start all processes at roughly the same time
        for p in processes:
            p.start()

        # Wait for all to complete
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

        # THE CRITICAL ASSERTION: All todos should be present
        app = TodoApp(db_path=db_path)
        final_todos = app.list()

        # This is the bug: without file locking, we may lose todos
        # because multiple processes can read the same initial state
        # and then overwrite each other's changes
        assert len(final_todos) == num_workers, (
            f"Expected {num_workers} todos, but only {len(final_todos)} were saved. "
            f"This indicates data loss due to non-atomic load-modify-save pattern."
        )

        # Verify all worker texts are present
        texts = {todo.text for todo in final_todos}
        for i in range(num_workers):
            expected_text = f"worker-{i}-todo"
            assert expected_text in texts, f"Missing todo from worker {i}"


def test_concurrent_add_with_initial_todos() -> None:
    """Test concurrent add() when there are existing todos.

    This tests the race condition more aggressively by starting with
    some existing todos, ensuring the initial state is non-empty.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.json")

        # Create initial todos
        app = TodoApp(db_path=db_path)
        initial_todos = []
        for i in range(3):
            initial_todos.append(app.add(f"initial-{i}"))

        num_workers = 5
        processes = []
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        for i in range(num_workers):
            p = multiprocessing.Process(target=_add_todo_worker, args=(100 + i, db_path, result_queue))
            processes.append(p)

        for p in processes:
            p.start()

        for p in processes:
            p.join(timeout=30)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        successes = [r for r in results if r[0] == "success"]
        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"Workers encountered errors: {errors}"
        assert len(successes) == num_workers

        # Final state should have initial + worker todos
        final_todos = app.list()
        expected_count = 3 + num_workers  # 3 initial + 5 workers

        assert len(final_todos) == expected_count, (
            f"Expected {expected_count} todos (3 initial + {num_workers} workers), "
            f"but only {len(final_todos)} were saved. Data was lost."
        )


def test_concurrent_mark_done() -> None:
    """Test that concurrent mark_done() operations don't cause data loss."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.json")

        # Create todos
        app = TodoApp(db_path=db_path)
        todos = []
        for i in range(5):
            todos.append(app.add(f"todo-{i}"))

        def mark_done_worker(todo_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
            try:
                app = TodoApp(db_path=db_path)
                app.mark_done(todo_id)
                result_queue.put(("success", todo_id))
            except Exception as e:
                result_queue.put(("error", todo_id, str(e)))

        processes = []
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        for todo in todos:
            p = multiprocessing.Process(target=mark_done_worker, args=(todo.id, db_path, result_queue))
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

        # All todos should still be present and marked done
        final_todos = app.list()
        assert len(final_todos) == 5, f"Expected 5 todos, got {len(final_todos)}"
        # All should be done
        for todo in final_todos:
            assert todo.done, f"Todo {todo.id} should be done"
