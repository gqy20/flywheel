"""Regression test for issue #5516: Concurrent add() produces unique IDs.

This test verifies that file locking is used to protect the load-compute-save
sequence when adding todos, ensuring that concurrent add operations produce
unique IDs and don't lose data.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add() operations produce unique IDs.

    Two processes simultaneously calling add() should result in
    two todos with different IDs, not one overwriting the other.
    """
    db_path = tmp_path / "concurrent.json"

    def add_worker(worker_id: int, text: str, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo and reports the result."""
        try:
            app = TodoApp(db_path=str(db_path))
            todo = app.add(text)
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Use a barrier to synchronize start
    barrier = multiprocessing.Barrier(2)
    results = multiprocessing.Queue()

    def sync_add_worker(worker_id: int, text: str) -> None:
        barrier.wait()  # Synchronize both processes to start at same time
        add_worker(worker_id, text, results)

    # Start two processes that will add todos simultaneously
    p1 = multiprocessing.Process(target=sync_add_worker, args=(1, "todo from process 1"))
    p2 = multiprocessing.Process(target=sync_add_worker, args=(2, "todo from process 2"))

    p1.start()
    p2.start()

    p1.join(timeout=10)
    p2.join(timeout=10)

    # Collect results
    all_results = []
    while not results.empty():
        all_results.append(results.get())

    # Verify both succeeded
    successes = [r for r in all_results if r[0] == "success"]
    errors = [r for r in all_results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"

    # Verify IDs are unique
    ids = [r[2] for r in successes]
    assert len(set(ids)) == 2, f"Expected 2 unique IDs, got {ids}"

    # Verify both todos exist in storage
    storage = TodoStorage(str(db_path))
    todos = storage.load()
    assert len(todos) == 2, f"Expected 2 todos in storage, got {len(todos)}"

    # Verify both texts are present (no data loss)
    texts = {todo.text for todo in todos}
    assert "todo from process 1" in texts
    assert "todo from process 2" in texts


def test_concurrent_add_multiple_workers(tmp_path: Path) -> None:
    """Test that multiple concurrent add() operations all succeed with unique IDs.

    This is a more aggressive test with more workers.
    """
    db_path = tmp_path / "multi_concurrent.json"
    num_workers = 5

    results = multiprocessing.Queue()
    barrier = multiprocessing.Barrier(num_workers)

    def add_worker_sync(worker_id: int) -> None:
        barrier.wait()
        try:
            app = TodoApp(db_path=str(db_path))
            todo = app.add(f"worker-{worker_id}-task")
            results.put(("success", worker_id, todo.id))
        except Exception as e:
            results.put(("error", worker_id, str(e)))

    processes = [
        multiprocessing.Process(target=add_worker_sync, args=(i,))
        for i in range(num_workers)
    ]

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=15)

    # Collect results
    all_results = []
    while not results.empty():
        all_results.append(results.get())

    successes = [r for r in all_results if r[0] == "success"]
    errors = [r for r in all_results if r[0] == "error"]

    # All should succeed
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    # All IDs should be unique
    ids = [r[2] for r in successes]
    assert len(set(ids)) == num_workers, f"Expected {num_workers} unique IDs, got {ids}"

    # Verify storage has all todos
    storage = TodoStorage(str(db_path))
    todos = storage.load()
    assert len(todos) == num_workers, f"Expected {num_workers} todos, got {len(todos)}"

    # Verify all texts are present (no data loss)
    texts = {todo.text for todo in todos}
    for i in range(num_workers):
        assert f"worker-{i}-task" in texts, f"Missing task from worker {i}"


def test_concurrent_mark_done_no_data_loss(tmp_path: Path) -> None:
    """Test that concurrent mark_done() on different todos doesn't lose data."""
    db_path = tmp_path / "mark_done.json"

    # Pre-populate with two todos
    storage = TodoStorage(str(db_path))
    storage.save([
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
    ])

    results = multiprocessing.Queue()
    barrier = multiprocessing.Barrier(2)

    def mark_done_worker(todo_id: int, worker_id: int) -> None:
        barrier.wait()
        try:
            app = TodoApp(db_path=str(db_path))
            app.mark_done(todo_id)
            results.put(("success", worker_id, todo_id))
        except Exception as e:
            results.put(("error", worker_id, str(e)))

    # Two processes mark different todos as done simultaneously
    p1 = multiprocessing.Process(target=mark_done_worker, args=(1, 1))
    p2 = multiprocessing.Process(target=mark_done_worker, args=(2, 2))

    p1.start()
    p2.start()

    p1.join(timeout=10)
    p2.join(timeout=10)

    # Collect results
    all_results = []
    while not results.empty():
        all_results.append(results.get())

    successes = [r for r in all_results if r[0] == "success"]
    errors = [r for r in all_results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"

    # Verify both todos are marked done
    todos = storage.load()
    assert len(todos) == 2, f"Expected 2 todos, got {len(todos)}"
    for todo in todos:
        assert todo.done, f"Todo {todo.id} should be marked done"


def test_sequential_add_still_works(tmp_path: Path) -> None:
    """Test that sequential add() operations still work correctly after locking."""
    db_path = tmp_path / "sequential.json"
    app = TodoApp(db_path=str(db_path))

    # Add several todos sequentially
    todo1 = app.add("first")
    todo2 = app.add("second")
    todo3 = app.add("third")

    # Verify IDs are sequential and unique
    assert todo1.id == 1
    assert todo2.id == 2
    assert todo3.id == 3

    # Verify all are in storage
    storage = TodoStorage(str(db_path))
    todos = storage.load()
    assert len(todos) == 3
    assert [t.text for t in todos] == ["first", "second", "third"]
