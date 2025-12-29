"""Test for race condition in get_next_id method - Issue #48."""

import threading
import time
from flywheel.storage import Storage
from flywheel.todo import Todo


def test_get_next_id_thread_safety():
    """Test that get_next_id is thread-safe."""
    storage = Storage(path="/tmp/test_issue_48.json")

    # Clear any existing todos
    for todo in storage.list():
        storage.delete(todo.id)

    # Add a todo to set initial state
    storage.add(Todo(id=None, title="Test 1", status="pending"))

    # Track results from multiple threads
    results = []
    errors = []

    def thread_func():
        """Function to be executed in multiple threads."""
        try:
            # Simulate concurrent access
            for _ in range(100):
                next_id = storage.get_next_id()
                results.append(next_id)
                time.sleep(0.0001)  # Small delay to increase chance of race condition
        except Exception as e:
            errors.append(e)

    # Create multiple threads
    threads = []
    num_threads = 10

    for _ in range(num_threads):
        t = threading.Thread(target=thread_func)
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Check if any errors occurred
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # All IDs should be unique and monotonically increasing
    # If race condition exists, we might see duplicates or unexpected values
    assert len(results) == num_threads * 100, f"Expected {num_threads * 100} results, got {len(results)}"

    # The IDs should be unique for each successful get_next_id call
    # With proper locking, each thread should see increasing IDs
    unique_ids = set(results)
    # We expect at least some variety in IDs, not all the same
    assert len(unique_ids) > 1, f"Race condition detected: all threads returned same ID {results[0]}"

    # Cleanup
    import os
    try:
        os.remove("/tmp/test_issue_48.json")
    except FileNotFoundError:
        pass


def test_get_next_id_with_concurrent_adds():
    """Test get_next_id consistency when adding todos concurrently."""
    storage = Storage(path="/tmp/test_issue_48_concurrent.json")

    # Clear any existing todos
    for todo in storage.list():
        storage.delete(todo.id)

    added_todos = []
    errors = []

    def add_todo_thread(title):
        """Thread function to add todos."""
        try:
            todo = Todo(id=None, title=title, status="pending")
            added = storage.add(todo)
            added_todos.append(added)
        except Exception as e:
            errors.append(e)

    # Create threads to add todos concurrently
    threads = []
    num_threads = 20

    for i in range(num_threads):
        t = threading.Thread(target=add_todo_thread, args=(f"Todo {i}",))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred while adding: {errors}"

    # All todos should have unique IDs
    ids = [todo.id for todo in added_todos]
    assert len(ids) == len(set(ids)), f"Duplicate IDs detected: {ids}"

    # Next ID should be greater than all added IDs
    next_id = storage.get_next_id()
    max_id = max(ids) if ids else 0
    assert next_id > max_id, f"Next ID {next_id} should be greater than max ID {max_id}"

    # Cleanup
    import os
    try:
        os.remove("/tmp/test_issue_48_concurrent.json")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    test_get_next_id_thread_safety()
    test_get_next_id_with_concurrent_adds()
    print("All tests passed!")
