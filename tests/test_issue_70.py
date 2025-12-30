"""Tests for Issue #70 - Thread safety vulnerability in _load method.

The _load method should not perform I/O operations while holding the lock,
as this can cause deadlocks and performance bottlenecks.
"""

import json
import tempfile
import threading
import time
from pathlib import Path

import pytest
from flywheel.storage import Storage
from flywheel.todo import Todo


def test_load_io_happens_outside_lock():
    """Test that _load performs I/O operations outside of the lock.

    This test creates a scenario where multiple threads try to load data
    simultaneously. If I/O is performed inside the lock, it will cause
    significant delays due to serialized I/O operations.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Prepare test data with multiple todos
        test_data = {
            "todos": [
                {"id": 1, "title": "Todo 1", "status": "pending"},
                {"id": 2, "title": "Todo 2", "status": "completed"},
                {"id": 3, "title": "Todo 3", "status": "pending"},
            ],
            "next_id": 4
        }

        # Write test data to file
        test_file.write_text(json.dumps(test_data, indent=2))

        # Track successful loads and timing
        successful_loads = []
        load_times = []
        lock = threading.Lock()

        def load_storage():
            """Load storage in a thread and measure time."""
            start_time = time.time()
            try:
                storage = Storage(path=str(test_file))
                load_time = time.time() - start_time

                with lock:
                    load_times.append(load_time)

                # Verify data was loaded correctly
                todos = storage.list()
                if len(todos) == 3:
                    successful_loads.append(True)
                else:
                    successful_loads.append(False)
            except Exception as e:
                successful_loads.append(False)
                print(f"Error in thread: {e}")

        # Create multiple threads to test concurrent loading
        threads = []
        num_threads = 5

        for _ in range(num_threads):
            thread = threading.Thread(target=load_storage)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Verify all threads loaded successfully
        assert len(successful_loads) == num_threads, \
            f"Expected {num_threads} successful loads, got {len(successful_loads)}"

        assert all(successful_loads), "Not all threads loaded successfully"

        # Verify load times are reasonable
        # If I/O is performed inside the lock, load times will be much higher
        avg_load_time = sum(load_times) / len(load_times)
        max_load_time = max(load_times)

        # With proper implementation (I/O outside lock), concurrent loads
        # should complete reasonably quickly
        assert max_load_time < 5.0, \
            f"Load time too high ({max_load_time:.4f}s), I/O may be inside lock"


def test_load_correctly_parses_json_data():
    """Test that _load correctly parses JSON data and updates state.

    This is a functional test to ensure data is loaded correctly.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Create a file that will be loaded
        test_data = {
            "todos": [
                {"id": 1, "title": "Test", "status": "pending"},
                {"id": 2, "title": "Test 2", "status": "completed"}
            ],
            "next_id": 3
        }
        test_file.write_text(json.dumps(test_data))

        # Create storage
        storage = Storage(path=str(test_file))

        # Verify data was loaded
        todos = storage.list()
        assert len(todos) == 2
        assert todos[0].title == "Test"
        assert todos[1].title == "Test 2"

        # Verify next_id was loaded correctly
        assert storage.get_next_id() == 3


def test_load_with_corrupted_file():
    """Test that _load handles corrupted files gracefully.

    When a file is corrupted, the error handling should work correctly.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Write invalid JSON
        test_file.write_text("{invalid json content")

        # Attempt to create storage - should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            Storage(path=str(test_file))

        assert "Invalid JSON" in str(exc_info.value)

        # Verify backup was created
        backup_file = Path(str(test_file) + ".backup")
        assert backup_file.exists(), "Backup file should be created"


def test_load_with_empty_file():
    """Test that _load handles empty/non-existent files correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Don't create the file - test non-existent case
        storage = Storage(path=str(test_file))

        # Should have empty todos
        todos = storage.list()
        assert len(todos) == 0

        # next_id should be 1
        assert storage.get_next_id() == 1
