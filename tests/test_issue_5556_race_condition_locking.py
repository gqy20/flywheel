"""Regression test for issue #5556: Race condition in TodoApp operations.

This test verifies that TodoApp operations (add, mark_done, remove) use proper
file-based locking to prevent data loss when multiple processes access the
storage concurrently.

The issue was that load-modify-save pattern without locking can cause:
- Lost updates when two processes read the same state and both write back
- ID collisions when two processes generate the same next_id
"""

from __future__ import annotations

import concurrent.futures
import time
from pathlib import Path

import pytest

from flywheel.cli import TodoApp


def test_concurrent_add_operations_preserve_all_todos(tmp_path: Path) -> None:
    """Test that concurrent add() operations don't lose data.

    This is a regression test for issue #5556. Without locking, if multiple
    processes call add() concurrently, some todos may be lost because:
    1. Process A loads todos []
    2. Process B loads todos []
    3. Process A adds todo with id=1 and saves
    4. Process B adds todo with id=1 and saves (overwrites A's work)

    With proper locking, all todos should be preserved with unique IDs.
    """
    db_path = tmp_path / "concurrent_add.json"

    def add_todo_worker(worker_id: int) -> tuple[int, int, str | None]:
        """Worker that adds a single todo and returns the result."""
        try:
            app = TodoApp(db_path=str(db_path))
            # Small delay to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))
            todo = app.add(f"todo-from-worker-{worker_id}")
            return (worker_id, todo.id, None)
        except Exception as e:
            return (worker_id, -1, str(e))

    num_threads = 10
    todos_per_thread = 10
    total_todos = num_threads * todos_per_thread

    # Use ThreadPoolExecutor for concurrent operations
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(add_todo_worker, thread_id * todos_per_thread + i)
            for thread_id in range(num_threads)
            for i in range(todos_per_thread)
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Check for errors
    errors = [r for r in results if r[2] is not None]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify all todos were saved (the key assertion)
    app = TodoApp(db_path=str(db_path))
    all_todos = app.list()

    # All todos should be preserved - this is the main assertion
    expected_count = total_todos
    assert len(all_todos) == expected_count, (
        f"Expected {expected_count} todos, but only {len(all_todos)} were saved. Race condition caused data loss."
    )

    # Verify all IDs are unique (no ID collisions)
    ids = [todo.id for todo in all_todos]
    assert len(ids) == len(set(ids)), (
        "ID collision detected - locking failed to prevent duplicate IDs"
    )


def test_concurrent_mark_done_operations(tmp_path: Path) -> None:
    """Test that concurrent mark_done() operations work correctly.

    Without locking, two processes marking different todos as done could
    result in only one change being saved.
    """
    db_path = tmp_path / "concurrent_done.json"

    # Pre-populate with todos
    app = TodoApp(db_path=str(db_path))
    for i in range(1, 21):
        app.add(f"initial-todo-{i}")

    def mark_done_worker(todo_id: int) -> tuple[int, bool, str | None]:
        """Worker that marks a todo as done."""
        try:
            app = TodoApp(db_path=str(db_path))
            app.mark_done(todo_id)
            return (todo_id, True, None)
        except Exception as e:
            return (todo_id, False, str(e))

    # Mark all todos as done concurrently using threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(mark_done_worker, i) for i in range(1, 21)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Check for errors
    errors = [r for r in results if r[2] is not None]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify all todos are marked as done
    app = TodoApp(db_path=str(db_path))
    all_todos = app.list()
    assert len(all_todos) == 20, f"Expected 20 todos, got {len(all_todos)}"
    for todo in all_todos:
        assert todo.done, f"Todo #{todo.id} was not marked as done - race condition"


def test_concurrent_remove_operations(tmp_path: Path) -> None:
    """Test that concurrent remove() operations work correctly.

    Without locking, removing todos concurrently could corrupt the file
    or cause unexpected behavior.
    """
    db_path = tmp_path / "concurrent_remove.json"

    # Pre-populate with todos
    app = TodoApp(db_path=str(db_path))
    for i in range(1, 21):
        app.add(f"initial-todo-{i}")

    def remove_worker(todo_id: int) -> tuple[int, bool, str | None]:
        """Worker that removes a todo."""
        try:
            app = TodoApp(db_path=str(db_path))
            app.remove(todo_id)
            return (todo_id, True, None)
        except Exception as e:
            return (todo_id, False, str(e))

    # Remove todos concurrently using threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(remove_worker, i) for i in range(1, 21)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Check for errors (one may fail if another thread already removed it)
    errors = [r for r in results if r[2] is not None and "not found" not in r[2]]
    assert len(errors) == 0, f"Workers encountered unexpected errors: {errors}"

    # Verify all todos are removed
    app = TodoApp(db_path=str(db_path))
    all_todos = app.list()
    assert len(all_todos) == 0, f"Expected 0 todos, got {len(all_todos)} - remove operations failed"


def test_lock_timeout_is_configurable(tmp_path: Path) -> None:
    """Test that lock acquisition has configurable timeout as per acceptance criteria."""
    db_path = tmp_path / "lock_timeout.json"

    # The TodoApp should accept a lock_timeout parameter
    app = TodoApp(db_path=str(db_path), lock_timeout=5.0)
    assert app.lock_timeout == 5.0, "TodoApp should accept lock_timeout parameter"


def test_lock_released_on_exception(tmp_path: Path) -> None:
    """Test that lock is properly released when an exception occurs.

    This verifies the deadlock prevention criterion: lock should be released
    even if an exception is raised during the operation.
    """
    db_path = tmp_path / "exception_lock.json"

    # Create a TodoApp and trigger an exception during add
    app = TodoApp(db_path=str(db_path))

    # First, add a todo successfully
    app.add("first-todo")

    # Now trigger an exception (empty text)
    with pytest.raises(ValueError, match="cannot be empty"):
        app.add("")  # Empty text should raise ValueError

    # The lock should have been released, so we can add another todo
    app.add("second-todo")

    # Verify both valid todos exist
    all_todos = app.list()
    assert len(all_todos) == 2
    assert all_todos[0].text == "first-todo"
    assert all_todos[1].text == "second-todo"
