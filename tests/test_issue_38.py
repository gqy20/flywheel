"""Test for race condition in add method (issue #38)."""

import threading
import tempfile
import os

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_add_same_todo_twice():
    """Test that adding the same Todo object twice doesn't cause issues."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test_issue_38.json")
        storage = Storage(storage_path)

        # Create a Todo object without ID
        todo = Todo(id=None, title="Test Todo", status="pending")

        # Add it first time
        result1 = storage.add(todo)

        # Try to add the same object again
        # Since todo now has an ID from the first add, it should be treated as an update
        # or should raise an error, but shouldn't cause data corruption
        result2 = storage.add(todo)

        # Verify the storage state is consistent
        all_todos = storage.list()
        unique_ids = set(t.id for t in all_todos)

        # The number of unique IDs should equal the number of todos
        # (no duplicate IDs allowed)
        assert len(unique_ids) == len(all_todos), \
            f"Duplicate IDs detected: {len(unique_ids)} unique IDs from {len(all_todos)} todos"


def test_concurrent_add_with_same_object():
    """Test concurrent adds with the same Todo object."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test_issue_38_concurrent.json")
        storage = Storage(storage_path)

        # Create a single Todo object without ID that will be shared
        shared_todo = Todo(id=None, title="Shared Todo", status="pending")

        results = []
        errors = []

        def add_todo():
            """Try to add the shared todo."""
            try:
                result = storage.add(shared_todo)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads trying to add the same todo
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=add_todo)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # There should be no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify storage state is consistent
        all_todos = storage.list()
        unique_ids = set(t.id for t in all_todos)

        # No duplicate IDs allowed
        assert len(unique_ids) == len(all_todos), \
            f"Duplicate IDs detected: {len(unique_ids)} unique IDs from {len(all_todos)} todos. IDs: {[t.id for t in all_todos]}"
