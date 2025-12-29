"""Test for race condition in ID generation (issue #17)."""

import threading
import tempfile
import os

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_concurrent_add_should_not_conflict():
    """Test that concurrent add operations don't create ID conflicts."""
    # Use a temporary file for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test_race.json")
        storage = Storage(storage_path)

        # Track results
        added_todos = []
        errors = []
        lock = threading.Lock()

        def add_todo(title: str):
            """Helper function to add a todo in a thread."""
            try:
                # Simulate race condition by calling get_next_id separately
                # This is the problematic pattern that causes ID conflicts
                todo_id = storage.get_next_id()
                # Small delay to increase chance of race condition
                import time
                time.sleep(0.001)
                # Now create and add the todo with the pre-obtained ID
                todo = Todo(id=todo_id, title=title, status="pending")
                result = storage.add(todo)
                with lock:
                    added_todos.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Create multiple threads that try to add todos simultaneously
        threads = []
        for i in range(10):
            thread = threading.Thread(target=add_todo, args=(f"Todo {i}",))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that there were no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Check that all todos were added
        assert len(added_todos) == 10, f"Expected 10 todos, got {len(added_todos)}"

        # Check that all IDs are unique
        ids = [t.id for t in added_todos]
        unique_ids = set(ids)
        assert len(unique_ids) == 10, f"ID conflict detected: {len(unique_ids)} unique IDs from 10 todos. IDs: {ids}"

        # Reload storage and verify persistence
        storage2 = Storage(storage_path)
        all_todos = storage2.list()
        assert len(all_todos) == 10, f"Expected 10 todos after reload, got {len(all_todos)}"

        # Verify all IDs are unique after reload
        reloaded_ids = [t.id for t in all_todos]
        unique_reloaded_ids = set(reloaded_ids)
        assert len(unique_reloaded_ids) == 10, f"ID conflict after reload: {len(unique_reloaded_ids)} unique IDs"
