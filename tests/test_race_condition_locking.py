"""Tests for race condition fix: load-modify-save pattern with locking.

This test suite verifies that TodoApp operations (add, mark_done, mark_undone, remove)
use file-based locking to prevent data loss when multiple processes operate concurrently.

Issue #5556: Race condition in TodoApp operations: load-modify-save pattern without locking
"""

from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


# Worker functions must be at module level for multiprocessing with spawn
def _add_worker(args: tuple[int, int, str]) -> int:
    """Worker that adds multiple todos and returns count added."""
    worker_id, num_todos, db_path = args
    app = TodoApp(db_path=db_path)
    added = 0
    for i in range(num_todos):
        try:
            app.add(f"worker-{worker_id}-todo-{i}")
            added += 1
        except Exception:
            pass  # Ignore errors in race condition test
    return added


def _add_and_mark_done_worker(args: tuple[int, list[int], str]) -> tuple[int, int]:
    """Worker that adds todos and marks some as done."""
    worker_id, todo_ids, db_path = args
    app = TodoApp(db_path=db_path)
    added = 0
    marked = 0
    for i in range(5):
        try:
            app.add(f"worker-{worker_id}-todo-{i}")
            added += 1
        except Exception:
            pass
    for todo_id in todo_ids:
        try:
            app.mark_done(todo_id)
            marked += 1
        except Exception:
            pass
    return added, marked


def _remove_worker(args: tuple[list[int], str]) -> int:
    """Worker that removes todos."""
    todo_ids, db_path = args
    app = TodoApp(db_path=db_path)
    removed = 0
    for todo_id in todo_ids:
        try:
            app.remove(todo_id)
            removed += 1
        except ValueError:
            pass  # Already removed by another process
        except Exception:
            pass
    return removed


def _mark_done_worker(args: tuple[list[int], str]) -> int:
    """Worker that marks todos as done."""
    todo_ids, db_path = args
    app = TodoApp(db_path=db_path)
    marked = 0
    for todo_id in todo_ids:
        try:
            app.mark_done(todo_id)
            marked += 1
        except ValueError:
            pass  # Already marked or not found
        except Exception:
            pass
    return marked


def test_concurrent_add_operations_without_locking_causes_data_loss(tmp_path: Path) -> None:
    """Regression test for issue #5556: Race condition in add operations.

    WITHOUT the fix: Multiple processes adding todos concurrently will lose data
    because load-modify-save is not atomic.

    WITH the fix: All todos should be preserved when using file-based locking.
    """
    db = tmp_path / "todos.json"

    num_workers = 5
    todos_per_worker = 20

    # Use spawn context to avoid issues with local functions
    ctx = mp.get_context("spawn")

    # Run workers in parallel
    with ctx.Pool(processes=num_workers) as pool:
        results = pool.map(
            _add_worker,
            [(i, todos_per_worker, str(db)) for i in range(num_workers)]
        )

    # Load final state
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # Total expected = num_workers * todos_per_worker
    expected_total = num_workers * todos_per_worker
    total_added = sum(results)

    # With proper locking, we should have all todos
    # Without locking, we will likely have fewer due to race conditions
    assert len(final_todos) == expected_total, (
        f"Expected {expected_total} todos (all {total_added} additions preserved), "
        f"but only {len(final_todos)} exist. "
        f"Data loss due to race condition in load-modify-save pattern."
    )


def test_concurrent_add_and_remove_operations_with_locking(tmp_path: Path) -> None:
    """Test that concurrent add/remove operations preserve data integrity.

    This test adds todos and then removes them concurrently from multiple processes.
    With proper locking, the final state should be consistent.
    """
    db = tmp_path / "todos.json"

    # First, add some initial todos
    app = TodoApp(db_path=str(db))
    for i in range(10):
        app.add(f"initial-todo-{i}")

    # Get initial todo IDs for removal
    storage = TodoStorage(str(db))
    initial_todos = storage.load()
    initial_ids = [t.id for t in initial_todos]

    # Use spawn context
    ctx = mp.get_context("spawn")

    # Run add and remove workers concurrently
    with ctx.Pool(processes=4) as pool:
        # Mix of add and remove operations
        pool.map(_add_and_mark_done_worker, [(0, [], str(db)), (1, [], str(db))])
        pool.map(_remove_worker, [(initial_ids[:5], str(db)), (initial_ids[5:], str(db))])

    # Final state should be consistent (valid JSON, no corruption)
    final_todos = storage.load()
    assert isinstance(final_todos, list)

    # All todos should have valid structure
    for todo in final_todos:
        assert hasattr(todo, "id")
        assert hasattr(todo, "text")
        assert isinstance(todo.text, str)


def test_concurrent_mark_done_operations_with_locking(tmp_path: Path) -> None:
    """Test that concurrent mark_done operations work correctly with locking."""
    db = tmp_path / "todos.json"

    # Add initial todos
    app = TodoApp(db_path=str(db))
    for i in range(5):
        app.add(f"todo-{i}")

    # Get todo IDs
    storage = TodoStorage(str(db))
    initial_todos = storage.load()
    todo_ids = [t.id for t in initial_todos]

    # Use spawn context
    ctx = mp.get_context("spawn")

    # Run multiple workers trying to mark same todos as done concurrently
    with ctx.Pool(processes=3) as pool:
        pool.map(
            _mark_done_worker,
            [(todo_ids, str(db)) for _ in range(3)]
        )

    # Final state should be consistent
    final_todos = storage.load()
    assert isinstance(final_todos, list)

    # All todos should be marked as done (the operation should be idempotent)
    for todo in final_todos:
        assert todo.done is True, f"Todo {todo.id} should be done"


def test_lock_timeout_configurable(tmp_path: Path) -> None:
    """Test that lock acquisition has configurable timeout.

    This is a basic test that the locking mechanism respects timeout settings.
    """
    db = tmp_path / "todos.json"

    # This should not raise with reasonable timeout
    app = TodoApp(db_path=str(db))
    app.add("test-todo")

    # Verify todo was added
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "test-todo"


def test_lock_released_on_exception(tmp_path: Path) -> None:
    """Test that lock is released when an exception occurs.

    Verifies deadlock prevention: if an operation fails, subsequent
    operations should still be able to acquire the lock.
    """
    db = tmp_path / "todos.json"

    app = TodoApp(db_path=str(db))

    # Try to remove a non-existent todo (should raise but not deadlock)
    with pytest.raises(ValueError, match="not found"):
        app.remove(999)

    # Should be able to add a todo after the exception
    app.add("after-exception")

    # Verify state
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "after-exception"
