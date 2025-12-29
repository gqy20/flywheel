"""Test for race condition in list method - Issue #42.

This test verifies that the list method is thread-safe and doesn't cause
race conditions when reading _todos without proper locking.
"""

import threading
import time
from flywheel.storage import Storage
from flywheel.todo import Todo


def test_list_thread_safety_with_concurrent_reads():
    """Test that list() is thread-safe during concurrent read operations.

    This test verifies that multiple threads can call list() simultaneously
    without causing race conditions or inconsistent reads.
    """
    storage = Storage(path="/tmp/test_issue_42.json")

    # Clear any existing todos
    for todo in storage.list():
        storage.delete(todo.id)

    # Add initial todos
    for i in range(20):
        storage.add(Todo(id=None, title=f"Todo {i}", status="pending"))

    errors = []
    results = []

    def list_thread():
        """Thread function that repeatedly calls list."""
        try:
            for _ in range(100):
                # List without filter
                todos = storage.list()
                results.append(len(todos))

                # List with status filter
                pending = storage.list(status="pending")
                results.append(len(pending))

                # Small delay to increase chance of race condition
                time.sleep(0.0001)
        except Exception as e:
            errors.append(e)

    # Create multiple threads
    threads = []
    num_threads = 10

    for _ in range(num_threads):
        t = threading.Thread(target=list_thread)
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Race condition detected - errors: {errors}"

    # Verify results are consistent
    assert len(results) > 0, "No results collected"

    # Final verification
    final_todos = storage.list()
    final_pending = storage.list(status="pending")

    # Manual count for verification
    manual_pending_count = sum(1 for t in final_todos if t.status == "pending")
    assert len(final_pending) == manual_pending_count, \
        f"Inconsistent state: list(status='pending')={len(final_pending)} but count={manual_pending_count}"

    # Cleanup
    import os
    try:
        os.remove("/tmp/test_issue_42.json")
    except FileNotFoundError:
        pass


def test_list_during_concurrent_writes():
    """Test that list() doesn't crash or return corrupted data during writes.

    This test verifies that list() properly uses locks to prevent reading
    _todos while it's being modified by other operations.
    """
    storage = Storage(path="/tmp/test_issue_42_writes.json")

    # Clear any existing todos
    for todo in storage.list():
        storage.delete(todo.id)

    errors = []
    list_results = []

    def read_thread():
        """Thread that reads todos."""
        try:
            for _ in range(50):
                todos = storage.list()
                list_results.append(len(todos))

                # Also test with status filter
                pending = storage.list(status="pending")
                list_results.append(len(pending))

                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    def write_thread():
        """Thread that modifies todos."""
        try:
            for i in range(50):
                # Add todos
                storage.add(Todo(id=None, title=f"Concurrent {i}", status="pending"))

                # Update todos
                todos = storage.list()
                if todos:
                    todo = todos[0]
                    updated = Todo(id=todo.id, title=todo.title, status="completed")
                    storage.update(updated)

                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    # Create threads
    threads = []
    num_read_threads = 5
    num_write_threads = 3

    for _ in range(num_read_threads):
        t = threading.Thread(target=read_thread)
        threads.append(t)
        t.start()

    for _ in range(num_write_threads):
        t = threading.Thread(target=write_thread)
        threads.append(t)
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Verify no errors
    assert len(errors) == 0, f"Errors during concurrent operations: {errors}"

    # Verify list operations completed successfully
    assert len(list_results) > 0, "No list results collected"

    # Final consistency check
    final_todos = storage.list()
    final_pending = storage.list(status="pending")

    # Verify the list operation doesn't return corrupted data
    assert isinstance(final_todos, list), "list() should return a list"
    assert isinstance(final_pending, list), "list(status=...) should return a list"

    # Verify all todos are valid
    for todo in final_todos:
        assert hasattr(todo, 'id'), "Todo should have an id attribute"
        assert hasattr(todo, 'title'), "Todo should have a title attribute"
        assert hasattr(todo, 'status'), "Todo should have a status attribute"

    # Cleanup
    import os
    try:
        os.remove("/tmp/test_issue_42_writes.json")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    test_list_thread_safety_with_concurrent_reads()
    test_list_during_concurrent_writes()
    print("All issue #42 tests passed!")
