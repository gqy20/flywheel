"""Regression tests for Issue #5668: Race condition in mark_done/mark_undone/remove.

This test file verifies that concurrent modifications to the todo storage
do not result in lost updates. The load-modify-save pattern must use
file-based locking to prevent race conditions.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_operations_no_lost_updates(tmp_path: Path) -> None:
    """Issue #5668: Concurrent add operations should not lose any todos.

    Test scenario:
    - Process A adds todo #1
    - Process B adds todo #2
    - Both operations happen concurrently
    - Final result should contain BOTH todos (no lost update)
    """
    db_path = str(tmp_path / "concurrent_add.json")

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a unique todo."""
        try:
            app = TodoApp(db_path)
            todo = app.add(f"worker-{worker_id}-todo")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently adding todos
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start all processes at roughly the same time
    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, result_queue))
        processes.append(p)

    for p in processes:
        p.start()

    # Wait for completion
    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    # All workers should succeed
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # CRITICAL: Verify ALL todos are present (no lost updates)
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    assert len(final_todos) == num_workers, (
        f"Expected {num_workers} todos after concurrent adds, got {len(final_todos)}. "
        f"This indicates lost updates due to race condition."
    )

    # Verify all worker texts are present
    texts = {todo.text for todo in final_todos}
    for i in range(num_workers):
        expected_text = f"worker-{i}-todo"
        assert expected_text in texts, f"Missing todo from worker {i}: lost update detected"


def test_concurrent_mark_done_operations_no_lost_updates(tmp_path: Path) -> None:
    """Issue #5668: Concurrent mark_done on different todos should both succeed.

    Test scenario:
    - Pre-populate storage with todos #1 and #2 (both undone)
    - Process A marks #1 done
    - Process B marks #2 done
    - Both operations happen concurrently
    - Final result should have BOTH todos marked done
    """
    db_path = str(tmp_path / "concurrent_done.json")

    # Pre-populate with two todos
    storage = TodoStorage(db_path)
    storage.save(
        [
            Todo(id=1, text="todo-1", done=False),
            Todo(id=2, text="todo-2", done=False),
        ]
    )

    def mark_done_worker(todo_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that marks a specific todo as done."""
        try:
            app = TodoApp(db_path)
            app.mark_done(todo_id)
            result_queue.put(("success", todo_id))
        except Exception as e:
            result_queue.put(("error", todo_id, str(e)))

    # Run two workers concurrently marking different todos as done
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    for todo_id in [1, 2]:
        p = multiprocessing.Process(target=mark_done_worker, args=(todo_id, result_queue))
        processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # CRITICAL: Verify BOTH todos are marked done
    final_todos = storage.load()
    assert len(final_todos) == 2, f"Expected 2 todos, got {len(final_todos)}"

    todo_by_id = {t.id: t for t in final_todos}
    assert todo_by_id[1].done is True, "Todo #1 should be done - race condition lost update"
    assert todo_by_id[2].done is True, "Todo #2 should be done - race condition lost update"


def test_concurrent_mark_done_and_undone_different_todos(tmp_path: Path) -> None:
    """Issue #5668: Concurrent mark_done and mark_undone on different todos should both succeed.

    Test scenario:
    - Pre-populate with todo #1 (undone) and todo #2 (done)
    - Process A marks #1 done
    - Process B marks #2 undone
    - Both operations happen concurrently
    - Final result: #1 done, #2 undone
    """
    db_path = str(tmp_path / "concurrent_mixed.json")

    # Pre-populate
    storage = TodoStorage(db_path)
    storage.save(
        [
            Todo(id=1, text="todo-1", done=False),
            Todo(id=2, text="todo-2", done=True),
        ]
    )

    def mark_done_worker(result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path)
            app.mark_done(1)
            result_queue.put(("done_success",))
        except Exception as e:
            result_queue.put(("done_error", str(e)))

    def mark_undone_worker(result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path)
            app.mark_undone(2)
            result_queue.put(("undone_success",))
        except Exception as e:
            result_queue.put(("undone_error", str(e)))

    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=mark_done_worker, args=(result_queue,))
    p2 = multiprocessing.Process(target=mark_undone_worker, args=(result_queue,))

    p1.start()
    p2.start()
    p1.join(timeout=10)
    p2.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if "error" in r[0]]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify final state
    final_todos = storage.load()
    todo_by_id = {t.id: t for t in final_todos}

    assert todo_by_id[1].done is True, "Todo #1 should be done"
    assert todo_by_id[2].done is False, "Todo #2 should be undone"


def test_concurrent_add_and_remove_operations(tmp_path: Path) -> None:
    """Issue #5668: Concurrent add and remove should not lose data.

    Test scenario:
    - Pre-populate with todo #1
    - Process A removes todo #1
    - Process B adds a new todo
    - Both operations happen concurrently
    - Final result: todo #1 removed, new todo present
    """
    db_path = str(tmp_path / "concurrent_add_remove.json")

    # Pre-populate
    storage = TodoStorage(db_path)
    storage.save([Todo(id=1, text="original", done=False)])

    def remove_worker(result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path)
            app.remove(1)
            result_queue.put(("remove_success",))
        except Exception as e:
            result_queue.put(("remove_error", str(e)))

    def add_worker(result_queue: multiprocessing.Queue) -> None:
        try:
            app = TodoApp(db_path)
            app.add("new-todo")
            result_queue.put(("add_success",))
        except Exception as e:
            result_queue.put(("add_error", str(e)))

    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=remove_worker, args=(result_queue,))
    p2 = multiprocessing.Process(target=add_worker, args=(result_queue,))

    p1.start()
    p2.start()
    p1.join(timeout=10)
    p2.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if "error" in r[0]]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Verify final state - should have only the new todo
    final_todos = storage.load()

    # Either: original removed and new added (1 todo)
    # Or: original still there and new added (2 todos) if remove happened before add loaded
    # But NEVER: original still there and new NOT added (lost update)
    texts = {t.text for t in final_todos}
    assert "new-todo" in texts, "New todo should be present - lost update on add"


def test_file_integrity_after_concurrent_operations(tmp_path: Path) -> None:
    """Issue #5668: File must contain valid JSON after concurrent operations.

    This is a safety test to ensure the file is never corrupted.
    """
    db_path = str(tmp_path / "integrity.json")

    def stress_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that performs multiple operations."""
        try:
            app = TodoApp(db_path)
            for i in range(3):
                app.add(f"worker-{worker_id}-todo-{i}")
                time.sleep(0.001)
            result_queue.put(("success", worker_id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    num_workers = 3
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    processes = []

    for i in range(num_workers):
        p = multiprocessing.Process(target=stress_worker, args=(i, result_queue))
        processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=15)

    # Verify file is valid JSON and contains todos
    storage = TodoStorage(db_path)
    final_todos = storage.load()

    assert isinstance(final_todos, list), "Final data should be a list"
    # All todos should have valid structure
    for todo in final_todos:
        assert hasattr(todo, "id"), "Todo should have id"
        assert hasattr(todo, "text"), "Todo should have text"
