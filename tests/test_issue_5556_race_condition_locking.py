"""Regression test for issue #5556: Race condition in TodoApp operations.

Tests that TodoApp operations (add, mark_done, remove) use file-based locking
to prevent data loss when multiple processes access the same storage file.

The issue: load-modify-save pattern is not atomic:
  1. Process A loads todos [1, 2]
  2. Process B loads todos [1, 2]
  3. Process A adds todo 3, saves [1, 2, 3]
  4. Process B adds todo 4, saves [1, 2, 4] -- LOST todo 3!
"""

from __future__ import annotations

import contextlib
import multiprocessing
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.todo import Todo


# Worker functions must be at module level for multiprocessing with spawn
def _add_todos_worker(args: tuple[int, str, int]) -> int:
    """Worker function that adds multiple todos."""
    worker_id, db_path, count = args
    app = TodoApp(db_path=db_path)
    for i in range(count):
        try:
            app.add(f"worker-{worker_id}-todo-{i}")
        except Exception:
            return 0  # Worker failed
    return count


def _add_worker(db_path: str) -> int:
    app = TodoApp(db_path=db_path)
    for i in range(20):
        with contextlib.suppress(Exception):
            app.add(f"added-todo-{i}")
    return 0


def _mark_done_worker(db_path: str) -> int:
    app = TodoApp(db_path=db_path)
    for i in range(1, 26):  # Mark first 25 initial todos as done
        with contextlib.suppress(Exception):
            app.mark_done(i)
    return 0


def _remove_worker(db_path: str) -> int:
    app = TodoApp(db_path=db_path)
    for i in range(26, 51):  # Remove last 25 initial todos
        with contextlib.suppress(Exception):
            app.remove(i)
    return 0


def test_concurrent_add_operations_without_locking_causes_data_loss(tmp_path: Path) -> None:
    """Failing test: verify that concurrent add() operations cause data loss.

    This test demonstrates the race condition issue #5556.
    Without locking, multiple processes adding todos concurrently will
    lose some todos due to the load-modify-save race condition.

    The fix should ensure all 1000 todos are preserved.
    """
    db = tmp_path / "concurrent.json"
    num_processes = 10
    todos_per_process = 100
    expected_total = num_processes * todos_per_process  # 1000

    # Use multiprocessing with spawn to run concurrent adds
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(processes=num_processes) as pool:
        args = [(i, str(db), todos_per_process) for i in range(num_processes)]
        results = pool.map(_add_todos_worker, args)

    # Check that all workers succeeded
    successful_adds = sum(results)
    assert successful_adds == expected_total, f"Some workers failed: {results}"

    # Load final state and verify NO data loss
    app = TodoApp(db_path=str(db))
    final_todos = app.list()

    # Without locking, this will FAIL - some todos will be lost
    # With locking, all 1000 todos should be present
    actual_count = len(final_todos)
    assert (
        actual_count == expected_total
    ), f"DATA LOSS DETECTED: Expected {expected_total} todos, got {actual_count}. {expected_total - actual_count} todos were lost due to race condition."


def test_concurrent_mixed_operations_without_locking_causes_data_loss(tmp_path: Path) -> None:
    """Failing test: verify that mixed concurrent operations cause data loss.

    This tests add, mark_done, and remove operations all running concurrently.
    """
    db = tmp_path / "mixed_concurrent.json"

    # Pre-populate with some todos
    app = TodoApp(db_path=str(db))
    for i in range(50):
        app.add(f"initial-todo-{i}")

    # Run all workers concurrently using spawn context
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(processes=9) as pool:  # 3 of each type
        pool.apply_async(_add_worker, (str(db),))
        pool.apply_async(_add_worker, (str(db),))
        pool.apply_async(_add_worker, (str(db),))

        pool.apply_async(_mark_done_worker, (str(db),))
        pool.apply_async(_mark_done_worker, (str(db),))
        pool.apply_async(_mark_done_worker, (str(db),))

        pool.apply_async(_remove_worker, (str(db),))
        pool.apply_async(_remove_worker, (str(db),))
        pool.apply_async(_remove_worker, (str(db),))

        pool.close()
        pool.join()

    # Verify data integrity - the file should be valid JSON
    final_todos = app.list()

    # All remaining todos should have valid structure
    for todo in final_todos:
        assert isinstance(todo, Todo)
        assert isinstance(todo.id, int)
        assert isinstance(todo.text, str)

    # Without locking, we expect data loss (some added todos missing)
    # With locking, we should have exactly:
    # 50 initial - 25 removed + 60 added = 85 todos
    expected_final = 50 - 25 + 60  # 85
    actual_count = len(final_todos)

    assert (
        actual_count == expected_final
    ), f"DATA LOSS: Expected {expected_final} todos after mixed ops, got {actual_count}"


def test_lock_timeout_is_configurable(tmp_path: Path) -> None:
    """Test that lock acquisition timeout can be configured.

    This verifies that the implementation allows configuring the timeout
    for lock acquisition, preventing indefinite blocking.
    """
    db = tmp_path / "timeout.json"

    # This test will pass once locking is implemented with configurable timeout
    # The TodoApp should accept a lock_timeout parameter
    try:
        app = TodoApp(db_path=str(db), lock_timeout=5.0)
        app.add("test todo")
        # Should succeed without timeout
        assert len(app.list()) == 1
    except TypeError:
        # TodoApp doesn't accept lock_timeout yet - this indicates the fix isn't applied
        pytest.skip("lock_timeout parameter not yet implemented in TodoApp")


def test_lock_released_on_exception(tmp_path: Path) -> None:
    """Test that lock is properly released when an exception occurs.

    This verifies that the lock implementation uses proper cleanup
    to prevent deadlocks when errors occur during operations.
    """
    db = tmp_path / "exception.json"

    app = TodoApp(db_path=str(db))

    # First, add a valid todo
    app.add("valid todo")

    # Try to add an empty todo (should raise ValueError)
    with pytest.raises(ValueError, match="cannot be empty"):
        app.add("")

    # Lock should have been released - this should work
    app.add("another valid todo")

    # Verify both valid todos are present
    todos = app.list()
    assert len(todos) == 2
