"""Test for issue #37 - Race condition in _load method."""

import os
import tempfile
import threading
from pathlib import Path

from flywheel.storage import Storage


def test_load_race_condition():
    """Test that _load is thread-safe when file doesn't exist."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test_todos.json")

        # Track if any exceptions occur
        exceptions = []

        def create_storage():
            """Create a Storage instance in a thread."""
            try:
                storage = Storage(path=storage_path)
                # Verify the storage was initialized correctly
                assert storage._todos == []
                assert storage.list() == []
            except Exception as e:
                exceptions.append(e)

        # Create multiple threads that all try to initialize Storage at the same time
        # This should trigger the race condition if _load is not thread-safe
        threads = []
        for _ in range(10):
            t = threading.Thread(target=create_storage)
            threads.append(t)

        # Start all threads simultaneously
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Check that no exceptions occurred
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

        # Verify the final state is correct
        storage = Storage(path=storage_path)
        assert storage._todos == []
        assert storage.list() == []


def test_load_with_existing_file_is_thread_safe():
    """Test that _load is thread-safe when file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test_todos.json")

        # Create a storage with some initial data
        storage1 = Storage(path=storage_path)
        from flywheel.todo import Todo
        storage1.add(Todo(id=1, title="Test todo", status="pending"))

        # Track if any exceptions occur
        exceptions = []
        results = []

        def load_storage():
            """Load a Storage instance in a thread."""
            try:
                storage = Storage(path=storage_path)
                todos = storage.list()
                results.append(len(todos))
                assert len(todos) == 1
                assert todos[0].title == "Test todo"
            except Exception as e:
                exceptions.append(e)

        # Create multiple threads that all try to load Storage at the same time
        threads = []
        for _ in range(10):
            t = threading.Thread(target=load_storage)
            threads.append(t)

        # Start all threads simultaneously
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Check that no exceptions occurred
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

        # All threads should have loaded 1 todo
        assert len(results) == 10
        assert all(r == 1 for r in results)
