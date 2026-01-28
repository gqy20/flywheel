"""Test file locking mechanism for multi-process safety (Issue #268).

This test verifies that the storage backend uses file-level locking
to prevent concurrent access from multiple processes.
"""

import multiprocessing
import tempfile
import time
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def worker_add_todos(storage_path, worker_id, num_todos, results_queue):
    """Worker function that adds todos from a separate process.

    Args:
        storage_path: Path to the storage file.
        worker_id: Identifier for this worker.
        num_todos: Number of todos to add.
        results_queue: Queue to report results back to parent.
    """
    try:
        # Each process creates its own Storage instance
        storage = Storage(path=storage_path)

        added_count = 0
        for i in range(num_todos):
            todo = Todo(title=f"Worker {worker_id} - Todo {i}", status="pending")
            storage.add(todo)
            added_count += 1

        results_queue.put(("success", worker_id, added_count))
    except Exception as e:
        results_queue.put(("error", worker_id, str(e)))


def test_multiprocess_concurrent_add():
    """Test that concurrent adds from multiple processes are safe.

    This test spawns multiple processes that simultaneously add todos.
    Without file locking, this can cause data corruption.

    With proper file locking:
    - No processes should encounter errors
    - All todos should be saved correctly
    - No data corruption should occur
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test_multiprocess.json")

        # Create initial storage
        storage = Storage(path=storage_path)
        storage.add(Todo(id=1, title="Initial Todo", status="pending"))

        # Number of worker processes and todos per worker
        num_workers = 4
        todos_per_worker = 10

        # Create a multiprocessing queue for results
        results_queue = multiprocessing.Queue()

        # Spawn worker processes
        processes = []
        for worker_id in range(num_workers):
            p = multiprocessing.Process(
                target=worker_add_todos,
                args=(storage_path, worker_id, todos_per_worker, results_queue)
            )
            processes.append(p)
            p.start()

        # Wait for all processes to complete
        for p in processes:
            p.join(timeout=30)
            if p.is_alive():
                # Process is still running - this might indicate deadlock
                p.terminate()
                p.join()

        # Collect results
        results = []
        errors = []
        while not results_queue.empty():
            result = results_queue.get()
            results.append(result)
            if result[0] == "error":
                errors.append(result)

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred in worker processes: {errors}"

        # Verify all workers reported success
        successful_workers = [r for r in results if r[0] == "success"]
        assert len(successful_workers) == num_workers, \
            f"Expected {num_workers} successful workers, got {len(successful_workers)}"

        # Reload storage and verify data integrity
        # Reload multiple times to catch potential corruption
        for retry in range(3):
            try:
                storage = Storage(path=storage_path)
                todos = storage.list()

                # Should have 1 initial + (num_workers * todos_per_worker) todos
                expected_count = 1 + (num_workers * todos_per_worker)
                assert len(todos) == expected_count, \
                    f"Expected {expected_count} todos, got {len(todos)} (attempt {retry + 1})"

                # Verify all todos have unique IDs
                todo_ids = [t.id for t in todos]
                assert len(todo_ids) == len(set(todo_ids)), \
                    f"Duplicate IDs found: {todo_ids} (attempt {retry + 1})"

                # Verify no data corruption (all todos should have valid titles)
                for todo in todos:
                    assert todo.title is not None, f"Todo {todo.id} has None title"
                    assert isinstance(todo.title, str), f"Todo {todo.id} has invalid title type"
                    assert len(todo.title) > 0, f"Todo {todo.id} has empty title"

                # If we get here, data is valid
                break
            except Exception as e:
                if retry == 2:
                    # Last attempt failed - raise the error
                    raise
                # Otherwise, retry (might be transient issue)
                time.sleep(0.1)


def worker_read_while_writing(storage_path, worker_id, results_queue):
    """Worker that reads while other processes write.

    Args:
        storage_path: Path to the storage file.
        worker_id: Identifier for this worker.
        results_queue: Queue to report results back to parent.
    """
    try:
        storage = Storage(path=storage_path)

        if worker_id % 2 == 0:
            # Even workers: read continuously
            success_count = 0
            for _ in range(50):
                todos = storage.list()
                # Verify data integrity while reading
                for todo in todos:
                    assert todo.id is not None
                    assert todo.title is not None
                success_count += 1
                time.sleep(0.001)
            results_queue.put(("success", worker_id, success_count))
        else:
            # Odd workers: write continuously
            success_count = 0
            for i in range(20):
                todo = Todo(title=f"Worker {worker_id} - Todo {i}", status="pending")
                storage.add(todo)
                success_count += 1
                time.sleep(0.001)
            results_queue.put(("success", worker_id, success_count))

    except Exception as e:
        results_queue.put(("error", worker_id, str(e)))


def test_multiprocess_read_write_concurrency():
    """Test concurrent reads and writes from multiple processes.

    This test verifies that file locking allows:
    - Multiple processes to read safely
    - Writers to exclude other writers
    - Writers to exclude readers (to prevent reading partial writes)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test_concurrent_rw.json")

        # Create initial storage with some todos
        storage = Storage(path=storage_path)
        for i in range(5):
            storage.add(Todo(title=f"Initial Todo {i}", status="pending"))

        # Number of worker processes
        num_workers = 6

        # Create a multiprocessing queue for results
        results_queue = multiprocessing.Queue()

        # Spawn worker processes
        processes = []
        for worker_id in range(num_workers):
            p = multiprocessing.Process(
                target=worker_read_while_writing,
                args=(storage_path, worker_id, results_queue)
            )
            processes.append(p)
            p.start()

        # Wait for all processes to complete
        for p in processes:
            p.join(timeout=30)
            if p.is_alive():
                p.terminate()
                p.join()

        # Collect results
        results = []
        errors = []
        while not results_queue.empty():
            result = results_queue.get()
            results.append(result)
            if result[0] == "error":
                errors.append(result)

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred during concurrent read/write: {errors}"

        # Verify all workers completed successfully
        successful_workers = [r for r in results if r[0] == "success"]
        assert len(successful_workers) == num_workers, \
            f"Expected {num_workers} successful workers, got {len(successful_workers)}"

        # Final verification - data should be intact
        storage = Storage(path=storage_path)
        todos = storage.list()

        # Should have at least the initial 5 todos
        assert len(todos) >= 5, f"Expected at least 5 todos, got {len(todos)}"

        # Verify all todos are valid
        for todo in todos:
            assert todo.id is not None, f"Todo has None ID"
            assert todo.title is not None, f"Todo {todo.id} has None title"
            assert isinstance(todo.title, str), f"Todo {todo.id} has invalid title type"


def worker_simultaneous_open(storage_path, worker_id, barrier, results_queue):
    """Worker that tries to open storage simultaneously.

    Args:
        storage_path: Path to the storage file.
        worker_id: Identifier for this worker.
        barrier: Barrier to synchronize opening.
        results_queue: Queue to report results back to parent.
    """
    try:
        # Wait at barrier so all processes start at roughly the same time
        barrier.wait()

        # All processes try to create Storage simultaneously
        storage = Storage(path=storage_path)

        # Try to add a todo
        todo = Todo(title=f"Worker {worker_id}", status="pending")
        storage.add(todo)

        results_queue.put(("success", worker_id))
    except Exception as e:
        results_queue.put(("error", worker_id, str(e)))


def test_multiprocess_simultaneous_open():
    """Test that multiple processes can open the same storage file safely.

    This test verifies that when multiple processes try to open
    the same storage file simultaneously, file locking prevents
    corruption and allows all processes to proceed.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test_simultaneous_open.json")

        # Create initial storage
        storage = Storage(path=storage_path)

        # Number of worker processes
        num_workers = 8

        # Barrier to synchronize all processes starting at the same time
        barrier = multiprocessing.Barrier(num_workers)

        # Create a multiprocessing queue for results
        results_queue = multiprocessing.Queue()

        # Spawn worker processes
        processes = []
        for worker_id in range(num_workers):
            p = multiprocessing.Process(
                target=worker_simultaneous_open,
                args=(storage_path, worker_id, barrier, results_queue)
            )
            processes.append(p)
            p.start()

        # Wait for all processes to complete
        for p in processes:
            p.join(timeout=30)
            if p.is_alive():
                p.terminate()
                p.join()

        # Collect results
        results = []
        errors = []
        while not results_queue.empty():
            result = results_queue.get()
            results.append(result)
            if result[0] == "error":
                errors.append(result)

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred during simultaneous open: {errors}"

        # Verify all workers completed successfully
        successful_workers = [r for r in results if r[0] == "success"]
        assert len(successful_workers) == num_workers, \
            f"Expected {num_workers} successful workers, got {len(successful_workers)}"

        # Final verification - data should be intact
        storage = Storage(path=storage_path)
        todos = storage.list()

        # All workers should have added their todo
        assert len(todos) == num_workers, f"Expected {num_workers} todos, got {len(todos)}"

        # Verify all todos are valid and have unique IDs
        todo_ids = [t.id for t in todos]
        assert len(todo_ids) == len(set(todo_ids)), f"Duplicate IDs found: {todo_ids}"
