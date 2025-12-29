"""Test thread safety of storage operations."""

import threading
import time
from flywheel.storage import Storage
from flywheel.todo import Todo


def test_get_method_thread_safety():
    """Test that get method is thread-safe and uses lock properly."""
    storage = Storage(path="/tmp/test_thread_safety_get.json")

    # Add a todo
    todo = Todo(id=1, title="Test Todo", status="pending")
    storage.add(todo)

    results = []
    errors = []

    def worker():
        """Worker that repeatedly calls get while another thread modifies storage."""
        try:
            for _ in range(100):
                result = storage.get(1)
                results.append(result)
                time.sleep(0.0001)  # Small delay to increase chance of race condition
        except Exception as e:
            errors.append(e)

    # Start multiple threads
    threads = []
    for _ in range(5):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Check that no errors occurred
    assert len(errors) == 0, f"Thread safety errors occurred: {errors}"

    # Check that all results are valid
    assert len(results) > 0, "No results returned"
    for result in results:
        assert result is not None, "get() returned None unexpectedly"
        assert result.id == 1, f"Expected ID 1, got {result.id}"
        assert result.title == "Test Todo", f"Expected 'Test Todo', got {result.title}"


def test_concurrent_get_and_add():
    """Test concurrent get and add operations for thread safety."""
    storage = Storage(path="/tmp/test_concurrent_get_add.json")

    errors = []
    get_results = []
    add_results = []

    def get_worker():
        """Worker that continuously gets todos."""
        try:
            for i in range(50):
                result = storage.get(1)
                get_results.append(result)
                time.sleep(0.0001)
        except Exception as e:
            errors.append(("get", e))

    def add_worker():
        """Worker that continuously adds todos."""
        try:
            for i in range(50):
                todo = Todo(title=f"Todo {i}", status="pending")
                result = storage.add(todo)
                add_results.append(result)
                time.sleep(0.0001)
        except Exception as e:
            errors.append(("add", e))

    # Start threads
    threads = []
    for _ in range(3):
        t1 = threading.Thread(target=get_worker)
        t2 = threading.Thread(target=add_worker)
        threads.extend([t1, t2])
        t1.start()
        t2.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Check for errors
    assert len(errors) == 0, f"Errors occurred during concurrent operations: {errors}"

    # Verify operations completed
    assert len(get_results) > 0, "No get operations completed"
    assert len(add_results) > 0, "No add operations completed"
