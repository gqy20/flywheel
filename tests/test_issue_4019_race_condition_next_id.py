"""Regression test for issue #4019: Race condition in next_id().

Tests that concurrent processes adding todos receive unique IDs,
preventing duplicate ID assignment in multi-process scenarios.
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_concurrent_add_produces_unique_ids(tmp_path: Path) -> None:
    """Regression test for issue #4019: Race condition in next_id().

    When two processes add todos simultaneously, each todo should have a unique ID.
    This test runs multiple processes that each add several todos concurrently
    to the same database file and verifies that all resulting IDs are unique.
    """
    import time

    db_path = tmp_path / "concurrent_todos.json"

    def add_todo_worker(
        worker_id: int, num_todos: int, result_queue: multiprocessing.Queue
    ) -> None:
        """Worker that adds multiple todos and reports their IDs."""
        try:
            storage = TodoStorage(str(db_path))
            added_ids = []
            for i in range(num_todos):
                todo = storage.add_todo_atomic(f"worker-{worker_id}-todo-{i}")
                added_ids.append(todo.id)
                # Small delay to increase race condition likelihood
                time.sleep(0.001)
            result_queue.put(("success", worker_id, added_ids))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run multiple workers concurrently, each adding todos
    num_workers = 3
    todos_per_worker = 5
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(
            target=add_todo_worker, args=(i, todos_per_worker, result_queue)
        )
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Verify no errors occurred
    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    # Collect all IDs from all workers
    all_ids: list[int] = []
    successes = [r for r in results if r[0] == "success"]
    for success in successes:
        _, _worker_id, added_ids = success
        all_ids.extend(added_ids)

    # Load final state and verify all IDs in storage
    storage = TodoStorage(str(db_path))
    final_todos = storage.load()
    final_ids = [todo.id for todo in final_todos]

    # Core assertion: all IDs must be unique (no duplicates)
    # This is the key verification for issue #4019
    assert len(all_ids) == len(set(all_ids)), (
        f"Duplicate IDs detected in concurrent additions! "
        f"IDs: {all_ids}, unique: {set(all_ids)}, duplicates: "
        f"{[i for i in all_ids if all_ids.count(i) > 1]}"
    )

    # Also verify the final storage state has unique IDs
    assert len(final_ids) == len(set(final_ids)), (
        f"Duplicate IDs in final storage! "
        f"IDs: {final_ids}, duplicates: {[i for i in final_ids if final_ids.count(i) > 1]}"
    )

    # Verify we got all the expected todos
    expected_total = num_workers * todos_per_worker
    assert len(final_ids) == expected_total, (
        f"Expected {expected_total} todos, got {len(final_ids)}"
    )


def test_next_id_with_file_based_generation(tmp_path: Path) -> None:
    """Test that add_todo_atomic generates unique IDs in concurrent scenarios.

    This is a more focused test that directly tests the atomic add method
    with concurrent file access, simulating the race condition.
    """
    db_path = tmp_path / "race_test.json"

    # Initialize with one todo
    storage = TodoStorage(str(db_path))
    storage.save([Todo(id=1, text="initial")])

    def add_todo_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
        """Worker that adds a todo atomically."""
        try:
            worker_storage = TodoStorage(str(db_path))
            # Use atomic add which handles locking internally
            todo = worker_storage.add_todo_atomic(f"worker-{worker_id}")
            result_queue.put(("success", worker_id, todo.id))
        except Exception as e:
            result_queue.put(("error", worker_id, str(e)))

    # Run concurrent workers
    num_workers = 4
    processes = []
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    for i in range(num_workers):
        p = multiprocessing.Process(target=add_todo_worker, args=(i, result_queue))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=10)

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    errors = [r for r in results if r[0] == "error"]
    assert len(errors) == 0, f"Workers encountered errors: {errors}"

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == num_workers, f"Expected {num_workers} successes, got {len(successes)}"

    assigned_ids = [s[2] for s in successes]
    # Verify that IDs assigned to successful writes are unique
    assert len(assigned_ids) == len(set(assigned_ids)), (
        f"Duplicate IDs were assigned in concurrent add_todo_atomic calls! "
        f"IDs: {assigned_ids}, duplicates: {[i for i in assigned_ids if assigned_ids.count(i) > 1]}"
    )

    # Final verification: load storage and check for ID uniqueness
    final_todos = storage.load()
    final_ids = [todo.id for todo in final_todos]
    assert len(final_ids) == len(set(final_ids)), (
        f"Final storage has duplicate IDs! "
        f"IDs: {final_ids}, duplicates: {[i for i in final_ids if final_ids.count(i) > 1]}"
    )

    # Verify we have the initial todo + all worker todos
    assert len(final_ids) == 1 + num_workers, (
        f"Expected {1 + num_workers} todos, got {len(final_ids)}"
    )
