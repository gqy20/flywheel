"""Test for issue #80 - deadlock in add method when todo_id exists."""

import threading
import time
from flywheel.storage import Storage
from flywheel.todo import Todo
import tempfile
import os


def test_add_duplicate_id_no_deadlock():
    """Test that add() doesn't cause deadlock when adding duplicate ID.

    This test verifies that when add() is called with a todo_id that already
    exists, it should raise ValueError without causing a deadlock.

    The bug was in storage.py line 202 where self.get(todo_id) was called
    while already holding self._lock, causing reentrant lock acquisition.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        storage = Storage(path=storage_path)

        # Add a todo with ID 1
        todo1 = Todo(id=1, title="First todo", status="pending")
        storage.add(todo1)

        # Try to add another todo with the same ID
        # This should raise ValueError, not deadlock
        todo2 = Todo(id=1, title="Second todo", status="pending")

        # Use a timeout to detect deadlock - if it hangs, the test will fail
        start_time = time.time()
        try:
            storage.add(todo2)
            # If we get here, no exception was raised - test should fail
            assert False, "Expected ValueError when adding duplicate ID"
        except ValueError as e:
            # Expected behavior
            assert "already exists" in str(e)
            elapsed = time.time() - start_time
            # Should complete quickly, not hang
            assert elapsed < 1.0, f"Operation took too long ({elapsed}s), possible deadlock"


def test_add_duplicate_id_multithreaded():
    """Test that add() doesn't cause deadlock in multithreaded scenario.

    This test verifies that even with multiple threads trying to add todos,
    there should be no deadlock when duplicate IDs are encountered.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        storage = Storage(path=storage_path)

        # Add initial todo
        todo1 = Todo(id=1, title="First todo", status="pending")
        storage.add(todo1)

        results = []
        errors = []

        def try_add_duplicate():
            """Try to add a duplicate ID from a thread."""
            try:
                todo = Todo(id=1, title="Duplicate", status="pending")
                storage.add(todo)
                results.append("success")
            except ValueError:
                results.append("expected_error")
            except Exception as e:
                errors.append(str(e))

        # Start thread with timeout
        thread = threading.Thread(target=try_add_duplicate)
        start_time = time.time()
        thread.start()
        thread.join(timeout=2.0)  # Should complete well within 2 seconds

        elapsed = time.time() - start_time

        # Verify thread completed (didn't deadlock)
        assert not thread.is_alive(), "Thread is still running - possible deadlock"
        assert elapsed < 2.0, f"Operation took too long ({elapsed}s), possible deadlock"
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert "expected_error" in results, "Expected ValueError for duplicate ID"


if __name__ == "__main__":
    test_add_duplicate_id_no_deadlock()
    test_add_duplicate_id_multithreaded()
    print("All tests passed!")
