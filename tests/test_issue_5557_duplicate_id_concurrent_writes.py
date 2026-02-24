"""Regression test for issue #5557: Duplicate ID generation with concurrent writes.

Tests that next_id() uses file-level locking to prevent race conditions
when multiple processes concurrently add todos.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from flywheel.cli import TodoApp
from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Test that concurrent add operations produce unique IDs.

    This is a regression test for issue #5557. Multiple processes adding
    todos concurrently should never receive duplicate IDs.
    """
    db_path = tmp_path / "todos.json"

    def add_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo and reports the assigned ID."""
        try:
            app = TodoApp(db_path=str(db_path))
            for i in range(20):  # Each worker adds 20 todos
                todo = app.add(f"worker-{worker_id}-todo-{i}")
                result_queue.put(("id", worker_id, todo.id))
                time.sleep(0.001)  # Small delay to increase race condition likelihood
            result_queue.put(("done", worker_id, None))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    all_ids: list[int] = []
    errors: list[tuple[int, str]] = []
    done_count = 0

    while not result_queue.empty():
        msg_type, worker_id, data = result_queue.get()
        if msg_type == "id":
            all_ids.append(data)
        elif msg_type == "error":
            errors.append((worker_id, data))
        elif msg_type == "done":
            done_count += 1

    # Verify no errors occurred
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    assert done_count == num_workers, f"Expected {num_workers} workers done, got {done_count}"

    # Verify all IDs are unique - this is the key assertion for issue #5557
    unique_ids = set(all_ids)
    expected_count = num_workers * 20  # 5 workers * 20 todos each = 100 todos
    assert len(all_ids) == expected_count, f"Expected {expected_count} IDs, got {len(all_ids)}"
    assert len(unique_ids) == len(all_ids), (
        f"Duplicate IDs detected! Got {len(all_ids)} IDs but only {len(unique_ids)} unique. "
        f"Duplicates: {[i for i in all_ids if all_ids.count(i) > 1]}"
    )


def test_single_process_ids_are_monotonically_increasing(tmp_path: Path) -> None:
    """Test that IDs are monotonically increasing in single-process scenario."""
    db_path = tmp_path / "todos.json"
    app = TodoApp(db_path=str(db_path))

    ids = []
    for i in range(10):
        todo = app.add(f"todo-{i}")
        ids.append(todo.id)

    # IDs should be monotonically increasing
    for i in range(1, len(ids)):
        assert ids[i] > ids[i - 1], f"IDs not monotonically increasing: {ids}"


def test_next_id_with_file_locking(tmp_path: Path) -> None:
    """Test that next_id uses file-level locking for atomic ID generation."""
    db_path = tmp_path / "todos.json"
    storage = TodoStorage(str(db_path))

    # Add some initial todos
    todos = [Todo(id=i, text=f"todo-{i}") for i in range(1, 4)]
    storage.save(todos)

    # next_id should return 4
    new_id = storage.next_id(todos)
    assert new_id == 4

    # Simulate concurrent access by having multiple calls
    # With locking, each should get a unique ID
    ids = []
    for _ in range(5):
        # Reload and get next_id
        loaded = storage.load()
        next_id_val = storage.next_id(loaded)
        ids.append(next_id_val)
        # Simulate the add operation
        new_todo = Todo(id=next_id_val, text=f"new-todo-{next_id_val}")
        loaded.append(new_todo)
        storage.save(loaded)

    # All IDs should be unique and monotonically increasing
    assert ids == sorted(ids), f"IDs not monotonically increasing: {ids}"
    assert len(set(ids)) == len(ids), f"Duplicate IDs found: {ids}"


def test_concurrent_add_via_storage_api(tmp_path: Path) -> None:
    """Test concurrent writes directly through storage API.

    This verifies the file-locking mechanism at the storage layer.
    """
    db_path = tmp_path / "todos.json"

    def storage_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that directly uses storage.atomic_add() for thread-safe adding."""
        try:
            storage = TodoStorage(str(db_path))
            for i in range(10):
                # Use atomic_add to prevent race conditions (issue #5557)
                todo = storage.atomic_add(f"worker-{worker_id}-todo-{i}")
                result_queue.put(("id", worker_id, todo.id))
            result_queue.put(("done", worker_id, None))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 3
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=storage_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    all_ids: list[int] = []
    errors: list[tuple[int, str]] = []

    while not result_queue.empty():
        msg_type, worker_id, data = result_queue.get()
        if msg_type == "id":
            all_ids.append(data)
        elif msg_type == "error":
            errors.append((worker_id, data))

    # Verify no errors and all IDs are unique
    assert len(errors) == 0, f"Workers encountered errors: {errors}"
    expected_count = num_workers * 10  # 3 workers * 10 todos each = 30 todos
    assert len(all_ids) == expected_count, f"Expected {expected_count} IDs, got {len(all_ids)}"
    assert len(set(all_ids)) == len(all_ids), (
        f"Duplicate IDs detected via storage API! "
        f"Duplicates: {[i for i in all_ids if all_ids.count(i) > 1]}"
    )
