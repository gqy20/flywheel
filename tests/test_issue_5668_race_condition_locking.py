"""Regression test for issue #5668: Race condition in mark_done/mark_undone/remove.

This test verifies that concurrent operations on the same todo file do not cause
lost updates. The issue is that load-modify-save pattern without locking can
cause one process's changes to be lost if another process modifies the file
between the load and save operations.

Acceptance criteria:
- Concurrent modifications to different todos should both be reflected
- Concurrent modifications to the same todo should not cause corruption
- File must always contain valid JSON after concurrent operations
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_operations_no_lost_todos(tmp_path: Path) -> None:
    """Test that concurrent add operations don't lose todos.

    Process A adds todo #1, Process B adds todo #2 concurrently.
    Both todos should be present in the final file.
    """
    db_path = tmp_path / "concurrent_add.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a unique todo."""
        try:
            app = TodoApp(str(db_path))
            todo = app.add(f"worker-{worker_id}-task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers that each add a todo
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
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

    # No errors should occur
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers

    # Verify all todos are present - this is the key assertion
    # Without locking, some todos may be lost due to race condition
    app = TodoApp(str(db_path))
    final_todos = app.list()

    # CRITICAL: All added todos should be present
    assert len(final_todos) == num_workers, (
        f"Lost updates detected! Expected {num_workers} todos, got {len(final_todos)}. "
        f"This indicates race condition in load-modify-save pattern."
    )


def test_concurrent_mark_done_different_todos(tmp_path: Path) -> None:
    """Test that concurrent mark_done on different todos preserves both states.

    Process A marks #1 done, Process B marks #2 done concurrently.
    Both todos should show correct done status.
    """
    db_path = tmp_path / "concurrent_done.json"

    # Pre-populate with todos
    app = TodoApp(str(db_path))
    app.add("task-1")
    app.add("task-2")

    def mark_done_worker(todo_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that marks a todo as done."""
        try:
            app = TodoApp(str(db_path))
            app.mark_done(todo_id)
            # Small delay to increase race likelihood
            time.sleep(0.001)
            result_queue.put(("success", todo_id, None))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    # Run workers that mark different todos as done concurrently
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    for todo_id in [1, 2]:
        p = multiprocessing.Process(target=mark_done_worker, args=(todo_id, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Verify both operations succeeded
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # CRITICAL: Both todos should be marked done
    final_todos = app.list()
    done_todos = [t for t in final_todos if t.done]
    assert len(done_todos) == 2, (
        f"Lost updates detected! Expected 2 done todos, got {len(done_todos)}. "
        f"This indicates race condition in mark_done load-modify-save pattern."
    )


def test_concurrent_add_and_mark_done(tmp_path: Path) -> None:
    """Test concurrent add and mark_done operations don't lose data.

    Process A adds a new todo, Process B marks an existing todo done concurrently.
    Both operations should succeed and data should be consistent.
    """
    db_path = tmp_path / "concurrent_mixed.json"

    # Pre-populate with one todo
    app = TodoApp(str(db_path))
    app.add("existing-task")

    def add_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a new todo."""
        try:
            app = TodoApp(str(db_path))
            app.add("new-task")
            result_queue.put(("success", "add", None))
        except Exception as e:
            result_queue.put(("error", "add", str(e)))

    def mark_done_worker(result_queue: multiprocessing.Queue) -> None:
        """Worker that marks existing todo done."""
        try:
            app = TodoApp(str(db_path))
            app.mark_done(1)
            result_queue.put(("success", "done", None))
        except Exception as e:
            result_queue.put(("error", "done", str(e)))

    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(target=add_worker, args=(result_queue,)),
        multiprocessing.Process(target=mark_done_worker, args=(result_queue,)),
    ]

    for p in processes:
        p.start()
    for p in processes:
        p.join(timeout=10)

    # Verify operations succeeded
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # CRITICAL: Both todos should be present, and first one should be done
    final_todos = app.list()
    assert len(final_todos) == 2, (
        f"Lost updates detected! Expected 2 todos, got {len(final_todos)}. "
        f"This indicates race condition in concurrent operations."
    )

    # The existing task should be marked done
    existing_task = [t for t in final_todos if t.text == "existing-task"]
    assert len(existing_task) == 1
    assert existing_task[0].done is True, (
        "Existing task should be marked done. "
        "Race condition may have caused lost update."
    )


def test_concurrent_remove_operations_no_corruption(tmp_path: Path) -> None:
    """Test that concurrent remove operations don't corrupt the file.

    While removing different todos concurrently, the file should remain
    valid JSON and contain consistent data.
    """
    db_path = tmp_path / "concurrent_remove.json"

    # Pre-populate with several todos
    app = TodoApp(str(db_path))
    for i in range(5):
        app.add(f"task-{i}")

    def remove_worker(todo_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that removes a todo."""
        try:
            app = TodoApp(str(db_path))
            app.remove(todo_id)
            result_queue.put(("success", todo_id, None))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    # Run workers that remove different todos concurrently
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    for todo_id in [1, 2, 3]:
        p = multiprocessing.Process(target=remove_worker, args=(todo_id, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Verify file is valid JSON and contains consistent data
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()

    # All remaining todos should have valid structure
    for todo in final_todos:
        assert hasattr(todo, "id")
        assert hasattr(todo, "text")
        assert isinstance(todo.id, int)
        assert isinstance(todo.text, str)

    # Should have fewer todos than we started with (some were removed)
    # The exact count depends on race conditions, but should be valid
    assert len(final_todos) >= 2, (
        f"Too many todos removed. Expected at least 2 remaining, got {len(final_todos)}."
    )
