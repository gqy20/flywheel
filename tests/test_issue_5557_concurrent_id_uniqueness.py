"""Regression test for issue #5557: Duplicate ID generation with concurrent writes.

This test verifies that concurrent todo additions from multiple processes
produce unique IDs without collisions.

Bug: next_id() computes max+1 from current list, causing race conditions
when two processes load the same state before either saves.

Fix: File-level locking ensures atomicity of load→next_id→save sequence.
"""

from __future__ import annotations

import multiprocessing
import tempfile
from pathlib import Path

from flywheel.cli import TodoApp


def test_concurrent_add_produces_unique_ids() -> None:
    """Test that concurrent todo additions produce unique IDs.

    This is the core regression test for issue #5557.

    Creates 100 todos from 5 concurrent processes, each adding 20 todos.
    Verifies all IDs are unique after all operations complete.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "todos.json"
        num_processes = 5
        todos_per_process = 20
        total_todos = num_processes * todos_per_process

        def add_todos_worker(
            worker_id: int,
            db_path_str: str,
            result_queue: multiprocessing.Queue,
        ) -> None:
            """Worker that adds multiple todos and returns IDs."""
            try:
                app = TodoApp(db_path=db_path_str)
                ids_added = []
                for i in range(todos_per_process):
                    todo = app.add(f"worker-{worker_id}-todo-{i}")
                    ids_added.append(todo.id)
                result_queue.put(("success", worker_id, ids_added))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        # Spawn and run all processes concurrently
        result_queue: multiprocessing.Queue = multiprocessing.Queue()
        processes = []
        for i in range(num_processes):
            p = multiprocessing.Process(
                target=add_todos_worker,
                args=(i, str(db_path), result_queue),
            )
            processes.append(p)
            p.start()

        # Wait for all processes
        for p in processes:
            p.join(timeout=30)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Check for errors
        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"Workers encountered errors: {errors}"

        # Verify all workers succeeded
        successes = [r for r in results if r[0] == "success"]
        assert len(successes) == num_processes, (
            f"Expected {num_processes} successes, got {len(successes)}"
        )

        # Collect all IDs
        all_ids = []
        for _, _worker_id, ids in successes:
            all_ids.extend(ids)

        # CRITICAL: All IDs must be unique
        assert len(all_ids) == total_todos, (
            f"Expected {total_todos} todos, got {len(all_ids)}"
        )
        unique_ids = set(all_ids)
        assert len(unique_ids) == len(all_ids), (
            f"Duplicate IDs detected! "
            f"Total: {len(all_ids)}, Unique: {len(unique_ids)}. "
            f"Duplicates: {[id for id in all_ids if all_ids.count(id) > 1]}"
        )


def test_single_process_ids_monotonically_increasing() -> None:
    """Test that IDs are monotonically increasing in single-process scenario.

    This is a sanity check to ensure the fix doesn't break normal operation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "todos.json"
        app = TodoApp(db_path=str(db_path))

        ids = []
        for i in range(10):
            todo = app.add(f"todo-{i}")
            ids.append(todo.id)

        # IDs should be 1, 2, 3, ..., 10
        assert ids == list(range(1, 11)), f"Expected [1..10], got {ids}"


def test_concurrent_add_maintains_data_integrity() -> None:
    """Test that concurrent additions don't corrupt the database.

    Even with locking, we need to ensure the final state is consistent.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "todos.json"
        num_processes = 3

        def add_single_todo_worker(
            worker_id: int,
            db_path_str: str,
            result_queue: multiprocessing.Queue,
        ) -> None:
            """Worker that adds a single todo."""
            try:
                app = TodoApp(db_path=db_path_str)
                todo = app.add(f"concurrent-todo-{worker_id}")
                result_queue.put(("success", worker_id, todo.id))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        # Spawn processes
        result_queue: multiprocessing.Queue = multiprocessing.Queue()
        processes = []
        for i in range(num_processes):
            p = multiprocessing.Process(
                target=add_single_todo_worker,
                args=(i, str(db_path), result_queue),
            )
            processes.append(p)
            p.start()

        # Wait and collect
        for p in processes:
            p.join(timeout=30)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Verify all succeeded
        successes = [r for r in results if r[0] == "success"]
        assert len(successes) == num_processes

        # Load final state and verify integrity
        app = TodoApp(db_path=str(db_path))
        final_todos = app.list()

        # Should have exactly num_processes todos
        assert len(final_todos) == num_processes, (
            f"Expected {num_processes} todos, got {len(final_todos)}"
        )

        # All IDs should be unique
        final_ids = [t.id for t in final_todos]
        assert len(set(final_ids)) == len(final_ids), "Final state has duplicate IDs"
