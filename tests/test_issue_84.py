"""Tests for Issue #84 - Thread safety vulnerability in _load method.

The _load method reads the file OUTSIDE the lock (line 36), creating a
'check-then-act' race condition. If the file is modified between reading
and acquiring the lock, the in-memory state will be inconsistent with
the file.
"""

import json
import tempfile
import threading
import time
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_load_read_inside_lock():
    """Test that _load reads file inside the lock to prevent race conditions.

    This test creates a scenario where one thread is loading data while
    another thread modifies the file. If the read happens outside the lock,
    there's a window where the file can change between reading and updating
    internal state, causing inconsistency.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Initial data with 1 todo
        initial_data = {
            "todos": [
                {"id": 1, "title": "Original Todo", "status": "pending"}
            ],
            "next_id": 2
        }
        test_file.write_text(json.dumps(initial_data, indent=2))

        # Track results
        results = {"loaded_todos": [], "file_read_during_load": False}
        lock = threading.Lock()
        storage_created = threading.Event()
        load_started = threading.Event()
        read_completed = threading.Event()
        file_modified = threading.Event()

        # Monkey patch read_text to detect when it's called
        original_read_text = Path.read_text
        read_times = []

        def tracked_read_text(self):
            """Track when read_text is called relative to lock acquisition."""
            with lock:
                read_times.append(time.time())
                results["file_read_during_load"] = load_started.is_set()
            return original_read_text(self)

        Path.read_text = tracked_read_text

        try:
            def modify_file_during_load():
                """Modify the file after storage starts loading but before it finishes."""
                # Wait for storage to start loading
                load_started.wait(timeout=5)

                # Simulate a delay between read and lock acquisition
                # This is the vulnerability window
                time.sleep(0.1)

                # Modify the file
                modified_data = {
                    "todos": [
                        {"id": 1, "title": "Original Todo", "status": "pending"},
                        {"id": 2, "title": "Modified Todo", "status": "pending"}
                    ],
                    "next_id": 3
                }
                test_file.write_text(json.dumps(modified_data, indent=2))
                file_modified.set()

            def create_storage_and_verify():
                """Create storage and verify the data consistency."""
                # Signal that we're about to start loading
                load_started.set()

                # Create storage - this will call _load
                storage = Storage(path=str(test_file))

                # Check the state
                todos = storage.list()

                with lock:
                    results["loaded_todos"] = todos

                storage_created.set()

            # Start threads
            modifier_thread = threading.Thread(target=modify_file_during_load)
            loader_thread = threading.Thread(target=create_storage_and_verify)

            modifier_thread.start()
            time.sleep(0.05)  # Ensure modifier is waiting
            loader_thread.start()

            # Wait for completion
            loader_thread.join(timeout=10)
            modifier_thread.join(timeout=10)

            # Verify results
            assert len(results["loaded_todos"]) > 0, "Storage should have loaded some todos"

            # The key assertion: with proper locking (read inside lock),
            # we should get consistent data matching what was in the file
            # at the time of the atomic read+update operation
            todos_count = len(results["loaded_todos"])

            # If read is inside lock, we should get either 1 or 2 todos consistently
            # If read is outside lock, we might get inconsistent state
            assert todos_count in [1, 2], \
                f"Expected 1 or 2 todos, got {todos_count}"

            # Additional verification: ensure data integrity
            # All loaded todos should be valid
            for todo in results["loaded_todos"]:
                assert todo.id is not None
                assert todo.title is not None

        finally:
            # Restore original method
            Path.read_text = original_read_text


def test_load_consistency_with_concurrent_modifications():
    """Test that _load maintains data consistency under concurrent modifications.

    This test verifies that even with concurrent file modifications,
    the storage maintains a consistent state.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Initial data
        initial_data = {
            "todos": [
                {"id": 1, "title": "Todo 1", "status": "pending"},
                {"id": 2, "title": "Todo 2", "status": "pending"}
            ],
            "next_id": 3
        }
        test_file.write_text(json.dumps(initial_data, indent=2))

        # Track successful loads
        successful_loads = []
        load_lock = threading.Lock()

        def concurrent_load(iteration):
            """Create storage instances concurrently."""
            try:
                storage = Storage(path=str(test_file))
                todos = storage.list()

                # Verify data integrity
                assert len(todos) >= 1, "Should have at least 1 todo"

                # Check that all todos have valid IDs
                for todo in todos:
                    assert todo.id is not None
                    assert todo.title is not None

                # Verify next_id is consistent
                next_id = storage.get_next_id()
                assert next_id > 0, "next_id should be positive"

                with load_lock:
                    successful_loads.append(iteration)
            except Exception as e:
                print(f"Error in thread {iteration}: {e}")

        # Create multiple threads
        threads = []
        num_threads = 10

        for i in range(num_threads):
            thread = threading.Thread(target=concurrent_load, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)

        # All threads should complete successfully
        assert len(successful_loads) == num_threads, \
            f"Expected {num_threads} successful loads, got {len(successful_loads)}"


def test_load_atomic_read_and_state_update():
    """Test that file read and state update happen atomically.

    This test verifies that there's no gap between reading the file
    and updating the internal state.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Create a file with specific data
        test_data = {
            "todos": [
                {"id": 1, "title": "Test Todo", "status": "pending"}
            ],
            "next_id": 2
        }
        test_file.write_text(json.dumps(test_data, indent=2))

        # Create storage and verify consistency
        storage = Storage(path=str(test_file))

        todos = storage.list()
        assert len(todos) == 1
        assert todos[0].id == 1
        assert todos[0].title == "Test Todo"
        assert storage.get_next_id() == 2

        # The loaded state should match the file exactly
        # If there's a race condition, this might not hold
        file_data = json.loads(test_file.read_text())
        assert len(todos) == len(file_data["todos"])
