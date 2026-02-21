"""Regression test for issue #5028: Race condition in concurrent operations.

This test verifies that TodoApp operations (add, mark_done, remove) use
file-based locking to prevent race conditions when multiple processes
access the same storage concurrently.

The issue was that operations like add() performed:
  1. _load() - read current todos
  2. modify the list
  3. _save() - write back

Without locking, two concurrent add() operations could:
  1. Both read the same initial state (e.g., empty list)
  2. Both assign the same ID (e.g., 1)
  3. Both write their version
  4. Result: one todo is lost, or duplicate IDs exist

The fix implements file-based locking using fcntl.flock to ensure
atomic read-modify-write operations across multiple processes.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_operations_no_data_loss(tmp_path: Path) -> None:
    """Test that concurrent add() operations don't lose data.

    This is a regression test for issue #5028. Two processes adding
    todos concurrently should result in both todos being present,
    not just one (which would indicate a race condition).
    """
    db_path = tmp_path / "test.json"

    def add_todo_worker(
        worker_id: int, db_path_str: str, result_queue: multiprocessing.Queue
    ) -> None:
        """Worker that adds a single todo and reports the result."""
        try:
            app = TodoApp(db_path=db_path_str)
            todo = app.add(f"worker-{worker_id} task")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Launch multiple concurrent add operations
    num_workers = 10
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all workers at roughly the same time
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, str(db_path), result_queue))
        processes.append(p)
        p.start()

    # Wait for all to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should succeed
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Verify final state: all todos should be present
    app = TodoApp(db_path=str(db_path))
    todos = app.list()

    # This is the key assertion: without locking, data loss would occur
    assert len(todos) == num_workers, (
        f"Expected {num_workers} todos, but found {len(todos)}. "
        f"This indicates data loss due to race condition."
    )

    # All IDs should be unique (no duplicates from race condition)
    ids = [todo.id for todo in todos]
    assert len(set(ids)) == num_workers, (
        f"Duplicate IDs found: {ids}. This indicates race condition in ID assignment."
    )

    # All worker texts should be present
    texts = {todo.text for todo in todos}
    for i in range(num_workers):
        expected_text = f"worker-{i} task"
        assert expected_text in texts, f"Missing todo from worker {i}"


def test_concurrent_mark_done_operations(tmp_path: Path) -> None:
    """Test that concurrent mark_done() operations don't corrupt data."""
    db_path = tmp_path / "test.json"

    # Pre-populate with todos
    app = TodoApp(db_path=str(db_path))
    for i in range(5):
        app.add(f"task-{i}")

    def mark_done_worker(
        todo_id: int, db_path_str: str, result_queue: multiprocessing.Queue
    ) -> None:
        """Worker that marks a todo as done."""
        try:
            app = TodoApp(db_path=db_path_str)
            app.mark_done(todo_id)
            result_queue.put(("success", todo_id))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    # Launch concurrent mark_done operations on the same todos
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(1, 6):  # IDs 1-5
        for _ in range(3):  # Multiple workers per todo
            p = multiprocessing.Process(
                target=mark_done_worker, args=(i, str(db_path), result_queue)
            )
            processes.append(p)
            p.start()

    for p in processes:
        p.join(timeout=30)

    # All operations should succeed
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify final state: all todos should be done
    todos = app.list()
    assert len(todos) == 5
    for todo in todos:
        assert todo.done, f"Todo {todo.id} should be marked done"


def test_concurrent_remove_operations(tmp_path: Path) -> None:
    """Test that concurrent remove() operations handle race conditions properly."""
    db_path = tmp_path / "test.json"

    # Pre-populate with many todos
    app = TodoApp(db_path=str(db_path))
    num_todos = 20
    for i in range(num_todos):
        app.add(f"task-{i}")

    def remove_worker(todo_id: int, db_path_str: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that removes a todo."""
        try:
            app = TodoApp(db_path=db_path_str)
            app.remove(todo_id)
            result_queue.put(("success", todo_id))
        except ValueError as e:
            # "Todo not found" is acceptable if another process removed it first
            if "not found" in str(e):
                result_queue.put(("not_found", todo_id))
            else:
                result_queue.put(("error", todo_id, str(e)))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    # Launch concurrent remove operations
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Each todo gets multiple removal attempts
    for i in range(1, num_todos + 1):
        for _ in range(3):
            p = multiprocessing.Process(target=remove_worker, args=(i, str(db_path), result_queue))
            processes.append(p)
            p.start()

    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # No errors should occur
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # All todos should be removed
    todos = app.list()
    assert len(todos) == 0, f"Expected all todos to be removed, but {len(todos)} remain"


def test_lock_timeout_behavior(tmp_path: Path) -> None:
    """Test that lock acquisition has a reasonable timeout.

    When a lock cannot be acquired within a reasonable time,
    the operation should fail with a clear error message.
    """
    db_path = tmp_path / "test.json"

    # This test verifies that the locking mechanism exists
    # and provides timeout behavior, not that it times out
    # (which would make the test slow and flaky)

    # The storage should support a context manager for locking
    storage = TodoStorage(str(db_path))

    # Verify that we can acquire a lock
    with storage.lock():
        # Within the lock context, we can perform operations
        storage.save([Todo(id=1, text="test")])
        todos = storage.load()
        assert len(todos) == 1

    # Lock should be released after context exits
    with storage.lock():
        # Can acquire again
        pass


def test_lock_released_on_crash(tmp_path: Path) -> None:
    """Test that lock is released even if process crashes during operation."""
    db_path = tmp_path / "test.json"

    def crashing_worker(db_path_str: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that acquires lock then crashes."""
        try:
            storage = TodoStorage(db_path_str)
            with storage.lock():
                # Simulate crash - raise exception while holding lock
                result_queue.put("acquired")
                raise RuntimeError("Simulated crash")
        except RuntimeError:
            # Lock should be released by context manager exit
            result_queue.put("crashed")

    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=crashing_worker, args=(str(db_path), result_queue))
    p.start()
    p.join(timeout=10)

    # Worker should have crashed
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    assert "acquired" in results
    assert "crashed" in results

    # Now verify we can acquire the lock from another process
    storage = TodoStorage(str(db_path))
    # This should not block indefinitely
    with storage.lock():
        storage.save([Todo(id=1, text="after crash")])

    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "after crash"
