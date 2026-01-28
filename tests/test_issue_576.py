"""Test for race condition in directory creation (Issue #576).

This test verifies that _secure_all_parent_directories properly handles
concurrent directory creation to prevent TOCTOU (Time-of-Check-Time-of-Use)
race conditions.

The issue suggests:
1. Using O_CREAT | O_EXCL flags (applicable to files, not directories)
2. Or handling EEXIST robustly during concurrent startup

Ref: Issue #576
"""

import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_concurrent_directory_creation():
    """Test that concurrent Storage instances can create the same directory safely.

    This test simulates the scenario where multiple processes or threads
    attempt to create the same directory structure simultaneously.

    The current implementation uses os.makedirs with exist_ok=True, which
    should handle this race condition. This test verifies that behavior.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a path that doesn't exist
        storage_path = Path(tmpdir) / "nested" / "dirs" / "todos.json"

        # Track successful creations
        results = {"success": 0, "errors": []}
        lock = threading.Lock()

        def create_storage():
            """Create a Storage instance and add a todo."""
            try:
                storage = Storage(str(storage_path))
                storage.add(Todo(title="Test todo", status="pending"))
                with lock:
                    results["success"] += 1
            except Exception as e:
                with lock:
                    results["errors"].append(str(e))

        # Create multiple threads that all try to create the same directory
        threads = []
        num_threads = 10

        for _ in range(num_threads):
            t = threading.Thread(target=create_storage)
            threads.append(t)

        # Start all threads at once
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # All threads should succeed without errors
        assert results["success"] == num_threads, (
            f"Expected {num_threads} successful creations, "
            f"got {results['success']}. Errors: {results['errors']}"
        )

        # Verify the directory exists
        assert storage_path.parent.exists(), "Parent directory should exist"

        # Verify the file was created (at least one thread should have succeeded)
        assert storage_path.exists(), "Storage file should exist"


def test_directory_creation_with_exist_ok():
    """Test that os.makedirs with exist_ok=True handles race conditions.

    This test verifies the specific mechanism used in _secure_all_parent_directories
    to handle concurrent directory creation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test" / "nested" / "dir"

        # Track results
        results = {"created": 0, "errors": []}
        lock = threading.Lock()

        def create_directory():
            """Simulate _secure_all_parent_directories behavior."""
            try:
                old_umask = os.umask(0o077)
                try:
                    # This is what the current code does
                    os.makedirs(test_path, mode=0o700, exist_ok=True)
                    with lock:
                        results["created"] += 1
                finally:
                    os.umask(old_umask)
            except Exception as e:
                with lock:
                    results["errors"].append(str(e))

        # Create multiple threads
        threads = []
        num_threads = 20

        for _ in range(num_threads):
            t = threading.Thread(target=create_directory)
            threads.append(t)

        # Start all threads at once
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # All threads should succeed (exist_ok=True handles the race)
        assert results["created"] == num_threads, (
            f"Expected {num_threads} successful creations, "
            f"got {results['created']}. Errors: {results['errors']}"
        )

        # Verify directory exists
        assert test_path.exists(), "Directory should exist"


def test_eexist_error_handling():
    """Test that EEXIST errors are handled gracefully.

    This test verifies that even if os.makedirs raises FileExistsError
    (which happens with EEXIST), the code handles it properly.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "eexist_test" / "nested"

        # First, create the directory
        old_umask = os.umask(0o077)
        try:
            os.makedirs(test_path, mode=0o700, exist_ok=False)
        finally:
            os.umask(old_umask)

        # Now try to create it again with exist_ok=False
        # This should raise FileExistsError (EEXIST)
        try:
            old_umask = os.umask(0o077)
            try:
                os.makedirs(test_path, mode=0o700, exist_ok=False)
                assert False, "Expected FileExistsError"
            except FileExistsError:
                # This is expected - the fix handles this case
                pass
            finally:
                os.umask(old_umask)

        # With exist_ok=True, it should succeed
        old_umask = os.umask(0o077)
        try:
            os.makedirs(test_path, mode=0o700, exist_ok=True)
            # Should succeed without raising
        finally:
            os.umask(old_umask)


def test_umask_isolation_during_concurrent_creation():
    """Test that umask changes during concurrent directory creation don't interfere.

    This test verifies that the umask context manager properly isolates
    umask changes, even when multiple threads are creating directories.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "umask_test" / "nested"

        # Track original umask
        original_umask = os.umask(0o077)
        os.umask(original_umask)

        results = {"success": 0}
        lock = threading.Lock()

        def create_with_umask():
            """Create directory with controlled umask."""
            try:
                old_umask = os.umask(0o077)
                try:
                    os.makedirs(test_path, mode=0o700, exist_ok=True)
                    with lock:
                        results["success"] += 1
                finally:
                    os.umask(old_umask)
            except Exception as e:
                with lock:
                    results.setdefault("errors", []).append(str(e))

        # Create multiple threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=create_with_umask)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify umask was restored
        final_umask = os.umask(0o077)
        os.umask(final_umask)

        assert final_umask == original_umask, (
            f"Umask was not restored: expected {oct(original_umask)}, "
            f"got {oct(final_umask)}"
        )

        # All threads should succeed
        assert results["success"] == 10, f"Expected 10 successes, got {results['success']}"
        assert "errors" not in results, f"Unexpected errors: {results.get('errors')}"
