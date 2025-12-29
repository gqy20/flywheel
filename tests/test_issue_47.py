"""Test for race condition in list method - Issue #47."""

import threading
import time
from flywheel.storage import Storage
from flywheel.todo import Todo


def test_list_thread_safety():
    """Test that list is thread-safe and doesn't crash during concurrent operations."""
    storage = Storage(path="/tmp/test_issue_47.json")

    # Clear any existing todos
    for todo in storage.list():
        storage.delete(todo.id)

    # Add initial todos
    for i in range(10):
        storage.add(Todo(id=None, title=f"Todo {i}", status="pending"))

    # Track results from multiple threads
    list_results = []
    errors = []

    def list_thread_func():
        """Thread function that calls list repeatedly."""
        try:
            for _ in range(50):
                # Call list without filter
                todos = storage.list()
                list_results.append(len(todos))

                # Call list with status filter
                pending = storage.list(status="pending")
                list_results.append(len(pending))

                time.sleep(0.0001)  # Small delay to increase chance of race condition
        except Exception as e:
            errors.append(e)

    def modify_thread_func():
        """Thread function that modifies todos concurrently."""
        try:
            for i in range(50):
                # Add new todos
                storage.add(Todo(id=None, title=f"Concurrent Todo {i}", status="pending"))

                # Update some todos
                todos = storage.list()
                if todos:
                    todo = todos[0]
                    updated = Todo(id=todo.id, title=todo.title, status="completed")
                    storage.update(updated)

                time.sleep(0.0001)  # Small delay to increase chance of race condition
        except Exception as e:
            errors.append(e)

    # Create multiple threads for both listing and modifying
    threads = []
    num_list_threads = 5
    num_modify_threads = 3

    # Start list threads
    for _ in range(num_list_threads):
        t = threading.Thread(target=list_thread_func)
        threads.append(t)
        t.start()

    # Start modify threads
    for _ in range(num_modify_threads):
        t = threading.Thread(target=modify_thread_func)
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Check if any errors occurred
    # Race conditions might cause exceptions, crashes, or inconsistent data
    assert len(errors) == 0, f"Race condition detected - errors occurred: {errors}"

    # Verify data consistency
    # All list operations should have returned valid results
    assert len(list_results) > 0, "No list results collected"

    # Final state should be consistent
    final_todos = storage.list()
    final_pending = storage.list(status="pending")

    # The count of pending todos should match the filter
    manual_pending_count = sum(1 for t in final_todos if t.status == "pending")
    assert len(final_pending) == manual_pending_count, \
        f"Inconsistent state: list(status='pending') returned {len(final_pending)} but manual count is {manual_pending_count}"

    # Cleanup
    import os
    try:
        os.remove("/tmp/test_issue_47.json")
    except FileNotFoundError:
        pass


def test_list_consistency_under_concurrent_adds():
    """Test that list returns consistent data when todos are being added concurrently."""
    storage = Storage(path="/tmp/test_issue_47_consistency.json")

    # Clear any existing todos
    for todo in storage.list():
        storage.delete(todo.id)

    errors = []
    max_seen_count = [0]  # Use list to allow modification in nested function
    lock = threading.Lock()

    def add_thread_func():
        """Thread function to add todos."""
        try:
            for i in range(20):
                storage.add(Todo(id=None, title=f"Todo {threading.current_thread().ident}-{i}", status="pending"))
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    def list_thread_func():
        """Thread function to list and track maximum count."""
        try:
            for _ in range(100):
                todos = storage.list()
                with lock:
                    if len(todos) > max_seen_count[0]:
                        max_seen_count[0] = len(todos)
                time.sleep(0.001)
        except Exception as e:
            errors.append(e)

    # Create threads
    threads = []
    num_add_threads = 5
    num_list_threads = 5

    for _ in range(num_add_threads):
        t = threading.Thread(target=add_thread_func)
        threads.append(t)
        t.start()

    for _ in range(num_list_threads):
        t = threading.Thread(target=list_thread_func)
        threads.append(t)
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred: {errors}"

    # Verify final count matches what we expect
    final_todos = storage.list()
    expected_count = num_add_threads * 20
    assert len(final_todos) == expected_count, \
        f"Expected {expected_count} todos, got {len(final_todos)}"

    # Cleanup
    import os
    try:
        os.remove("/tmp/test_issue_47_consistency.json")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    test_list_thread_safety()
    test_list_consistency_under_concurrent_adds()
    print("All tests passed!")
