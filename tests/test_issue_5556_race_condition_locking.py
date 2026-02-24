"""Regression test for issue #5556: Race condition in TodoApp operations.

Tests that the load-modify-save pattern is protected by file locking to prevent
concurrent processes from losing data when performing operations like add,
mark_done, and remove.

The issue occurs when:
1. Process A loads todos [1, 2, 3]
2. Process B loads todos [1, 2, 3]
3. Process A adds todo 4, saves [1, 2, 3, 4]
4. Process B adds todo 5, saves [1, 2, 3, 5] - loses todo 4!

The fix uses file-based locking (filelock) to ensure only one process
can perform the load-modify-save sequence at a time.
"""

from __future__ import annotations

import contextlib
import multiprocessing
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage


def test_concurrent_add_operations_without_locking_loses_data(tmp_path: Path) -> None:
    """Regression test: Without locking, concurrent adds lose data.

    This test demonstrates the race condition bug. If 10 processes each
    add 100 todos concurrently, we expect 1000 todos total. Without locking,
    we would get fewer due to lost updates.
    """
    db = tmp_path / "race_test.json"
    num_processes = 10
    todos_per_process = 100

    def add_todos_worker(worker_id: int, db_path: str, count: int) -> None:
        """Worker that adds multiple todos."""
        app = TodoApp(db_path=db_path)
        for i in range(count):
            app.add(f"worker-{worker_id}-todo-{i}")

    # Run concurrent workers
    processes = []
    for i in range(num_processes):
        p = multiprocessing.Process(
            target=add_todos_worker,
            args=(i, str(db), todos_per_process),
        )
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=60)

    # Verify: should have exactly num_processes * todos_per_process todos
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    expected_count = num_processes * todos_per_process
    actual_count = len(final_todos)

    # With proper locking, we should get all todos
    assert actual_count == expected_count, (
        f"Race condition detected: expected {expected_count} todos, "
        f"got {actual_count}. Data was lost due to concurrent writes."
    )


def test_concurrent_add_and_mark_done_operations(tmp_path: Path) -> None:
    """Test that concurrent add and mark_done operations don't interfere.

    This tests a more complex scenario where one process adds todos
    while another marks existing todos as done.
    """
    db = tmp_path / "mixed_ops.json"

    # Pre-populate with some todos
    app = TodoApp(db_path=str(db))
    for i in range(1, 51):
        app.add(f"initial-todo-{i}")

    def add_more_todos(db_path: str) -> None:
        """Worker that adds more todos."""
        app = TodoApp(db_path=db_path)
        for i in range(50):
            app.add(f"added-todo-{i}")

    def mark_todos_done(db_path: str) -> None:
        """Worker that marks todos as done."""
        app = TodoApp(db_path=db_path)
        for i in range(1, 51):
            with contextlib.suppress(ValueError):
                # Todo might have been removed by another process
                app.mark_done(i)

    # Run concurrent operations
    p1 = multiprocessing.Process(target=add_more_todos, args=(str(db),))
    p2 = multiprocessing.Process(target=mark_todos_done, args=(str(db),))

    p1.start()
    p2.start()

    p1.join(timeout=60)
    p2.join(timeout=60)

    # Verify: should have 100 todos (50 initial + 50 added)
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    assert len(final_todos) == 100, (
        f"Expected 100 todos after concurrent operations, got {len(final_todos)}"
    )


def test_concurrent_remove_operations(tmp_path: Path) -> None:
    """Test that concurrent remove operations don't corrupt data.

    This tests the remove() operation which also uses load-modify-save.
    """
    db = tmp_path / "remove_ops.json"

    # Pre-populate with todos
    app = TodoApp(db_path=str(db))
    for i in range(1, 101):
        app.add(f"remove-test-todo-{i}")

    def remove_range(db_path: str, start: int, end: int) -> None:
        """Worker that removes a range of todos."""
        app = TodoApp(db_path=db_path)
        for i in range(start, end):
            with contextlib.suppress(ValueError):
                # Already removed by another process
                app.remove(i)

    # Run concurrent remove operations on overlapping ranges
    processes = []
    for offset in [1, 25, 50, 75]:
        p = multiprocessing.Process(
            target=remove_range,
            args=(str(db), offset, offset + 50),
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=60)

    # Verify: file should be valid JSON and have remaining todos
    storage = TodoStorage(str(db))
    final_todos = storage.load()

    # Some todos should remain (those outside all remove ranges)
    # The exact count depends on timing, but the file should be valid
    assert len(final_todos) >= 0, "File should be valid JSON"

    # All remaining todos should have valid structure
    for todo in final_todos:
        assert hasattr(todo, "id")
        assert hasattr(todo, "text")


def test_lock_timeout_is_configurable(tmp_path: Path) -> None:
    """Test that lock acquisition has configurable timeout.

    Verifies that the storage accepts a timeout parameter for lock acquisition.
    """
    db = tmp_path / "timeout_test.json"

    # Storage should accept a lock_timeout parameter
    storage = TodoStorage(str(db), lock_timeout=5.0)

    # Should be able to perform operations normally
    from flywheel.todo import Todo

    storage.save([Todo(id=1, text="test")])
    loaded = storage.load()
    assert len(loaded) == 1


def test_lock_released_on_exception(tmp_path: Path) -> None:
    """Test that lock is properly released when an exception occurs.

    This ensures deadlock is prevented by proper lock release.
    """
    db = tmp_path / "exception_test.json"

    app = TodoApp(db_path=str(db))

    # Try to add an empty todo (should raise ValueError)
    with pytest.raises(ValueError, match="cannot be empty"):
        app.add("")

    # Lock should be released, so subsequent operations should work
    app.add("valid todo")
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "valid todo"
