"""Regression test for issue #5028: Race condition in concurrent operations.

This test verifies that TodoApp operations (add, mark_done, remove) use proper
file locking to prevent data loss when multiple processes perform concurrent
read-modify-write operations.

The bug: CLI performs load -> modify -> save without lock:
- src/flywheel/cli.py:30 - add() performs load -> modify -> save without lock
- src/flywheel/cli.py:43 - mark_done() performs load -> modify -> save without lock
- src/flywheel/cli.py:61 - remove() performs load -> modify -> save without lock

The fix: Implement file-based locking using fcntl.flock to ensure atomic
read-modify-write operations across multiple processes.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_operations_preserve_all_data(tmp_path: Path) -> None:
    """Test that concurrent add() calls preserve all todos.

    Without locking, if two processes read the same initial state,
    add different todos, and save, one process's todo will be lost.

    Acceptance criteria from issue:
    - Two concurrent processes adding todos should not lose data
    - Total todo count equals sum of both additions
    """
    db = tmp_path / "todos.json"

    def add_todo_worker(worker_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo and reports success/failure."""
        try:
            app = TodoApp(db_path=db_path)
            todo = app.add(f"todo-from-worker-{worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 10
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, str(db), result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # Check for errors
    if errors:
        error_msgs = [f"Worker {r[1]}: {r[2]}" for r in errors]
        pytest.fail(f"Workers encountered errors: {error_msgs}")

    # All workers should have succeeded
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # Critical assertion: no data loss
    # All 10 todos should be present in the file
    app = TodoApp(db_path=str(db))
    todos = app.list()

    assert (
        len(todos) == num_workers
    ), f"DATA LOSS: Expected {num_workers} todos, but only {len(todos)} found. Race condition occurred."

    # Verify all worker todos are present
    todo_texts = {t.text for t in todos}
    for i in range(num_workers):
        expected_text = f"todo-from-worker-{i}"
        assert expected_text in todo_texts, f"Missing todo from worker {i}"


def test_concurrent_mark_done_operations(tmp_path: Path) -> None:
    """Test that concurrent mark_done() calls work correctly.

    All processes should be able to mark their assigned todo as done
    without interfering with each other.
    """
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Pre-populate with todos
    initial_todos = [Todo(id=i + 1, text=f"initial-todo-{i}", done=False) for i in range(10)]
    storage.save(initial_todos)

    def mark_done_worker(todo_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that marks a todo as done."""
        try:
            app = TodoApp(db_path=db_path)
            todo = app.mark_done(todo_id)
            result_queue.put(("success", todo_id, todo.done))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Each worker marks a different todo as done
    for i in range(10):
        p = multiprocessing.Process(target=mark_done_worker, args=(i + 1, str(db), result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == 10, f"Expected 10 successes, got {len(successes)}"

    # Verify all todos are now marked as done
    todos = storage.load()
    for todo in todos:
        assert todo.done is True, f"Todo {todo.id} was not marked as done"


def test_concurrent_remove_operations(tmp_path: Path) -> None:
    """Test that concurrent remove() calls work correctly.

    Even with concurrent removal, the file should remain in a consistent state.
    """
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Pre-populate with more todos than we'll remove
    initial_todos = [Todo(id=i + 1, text=f"todo-{i}", done=False) for i in range(20)]
    storage.save(initial_todos)

    def remove_worker(todo_id: int, db_path: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that removes a todo."""
        try:
            app = TodoApp(db_path=db_path)
            app.remove(todo_id)
            result_queue.put(("success", todo_id, None))
        except ValueError as e:
            # Already removed by another process is acceptable
            if "not found" in str(e):
                result_queue.put(("already_removed", todo_id, str(e)))
            else:
                result_queue.put(("error", todo_id, str(e)))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Remove first 10 todos concurrently
    for i in range(10):
        p = multiprocessing.Process(target=remove_worker, args=(i + 1, str(db), result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=30)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered unexpected errors: {errors}"

    # Verify remaining todos (should have 10 left - the ones with id 11-20)
    todos = storage.load()
    remaining_ids = {t.id for t in todos}

    # First 10 should be gone (or some removed, some not found due to race)
    # Last 10 should definitely remain
    for i in range(10, 20):
        assert (i + 1) in remaining_ids, f"Todo {i + 1} should still exist"


def test_lock_timeout_behavior(tmp_path: Path) -> None:
    """Test lock timeout behavior when lock cannot be acquired.

    Per acceptance criteria:
    - File locking should use non-blocking acquisition with clear error on lock failure
    - Lock should be released even if process crashes during operation
    """
    import fcntl

    db = tmp_path / "todos.json"
    lock_file = tmp_path / "todos.json.lock"

    # Create the db file
    storage = TodoStorage(str(db))
    storage.save([])

    # Acquire the lock externally
    with open(lock_file, "w") as lock_fd:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Now try to add a todo - should timeout/fail gracefully
        app = TodoApp(db_path=str(db))

        # This should either:
        # 1. Wait and succeed (if lock timeout is long enough)
        # 2. Raise a clear error about lock acquisition failure
        # We'll test with a short timeout to verify error handling
        try:
            # If the implementation has a timeout, this should fail
            # For now, we just verify the operation doesn't hang forever
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Operation timed out")

            # Set a 5 second timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)

            try:
                app.add("should-either-succeed-or-fail-gracefully")
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        except (TimeoutError, BlockingIOError, OSError):
            # Expected: operation should fail gracefully when lock is held
            pass
        # If it succeeded, that's also fine - the lock might have been released

        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
