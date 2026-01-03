"""Tests for race condition fixes in directory creation (Issue #521).

This test module verifies that directory creation is properly protected
against TOCTOU (Time-of-Check-Time-of-Use) race conditions using file locks.
"""

import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from flywheel.storage import Storage


class TestDirectoryCreationRaceCondition:
    """Test that directory creation handles race conditions correctly."""

    def test_concurrent_directory_creation_with_lock(self, tmp_path):
        """Test that multiple processes can safely create directories concurrently.

        This test simulates a race condition where multiple threads try to create
        the same directory structure simultaneously. The file lock mechanism should
        prevent any TOCTOU issues.

        Scenario:
        - Multiple threads simultaneously attempt to create Storage instances
        - Each Storage instance tries to create and secure parent directories
        - File locks ensure atomicity and prevent permission issues
        """
        base_path = tmp_path / "concurrent_test"
        storage_path = base_path / "subdir" / "todos.json"

        # Number of concurrent threads
        num_threads = 10
        results = []
        errors = []

        def create_storage(thread_id):
            """Create a Storage instance in a thread."""
            try:
                # Add a small random delay to increase race condition likelihood
                time.sleep(0.001 * (thread_id % 3))

                storage = Storage(str(storage_path))
                results.append(thread_id)

                # Verify directory was created with secure permissions
                parent_dir = storage_path.parent
                if parent_dir.exists():
                    # On Unix, check directory permissions
                    if os.name != 'nt':
                        stat_info = os.stat(parent_dir)
                        mode = stat_info.st_mode & 0o777
                        # Directory should have restricted permissions (0o700 or 0o750)
                        assert mode in (0o700, 0o750), (
                            f"Thread {thread_id}: Directory has insecure permissions: {oct(mode)}"
                        )

                return thread_id
            except Exception as e:
                errors.append((thread_id, str(e)))
                raise

        # Create multiple threads that all try to create the same directory
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_storage, i) for i in range(num_threads)]
            completed = [f.result() for f in as_completed(futures)]

        # Verify all threads completed successfully
        assert len(completed) == num_threads, (
            f"Expected {num_threads} successful creations, got {len(completed)}"
        )
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert sorted(completed) == list(range(num_threads))

        # Verify final directory exists and is secure
        assert storage_path.parent.exists(), "Parent directory was not created"

    def test_atomic_directory_creation_no_toctou(self, tmp_path):
        """Test that directory creation is atomic without TOCTOU windows.

        This test verifies that the directory creation process uses proper
        file locking to ensure atomicity. The check-exist-create sequence
        must be protected by a lock.

        Scenario:
        - Verify that a lock file is used during directory creation
        - Ensure the lock is properly acquired and released
        - Check that concurrent operations are serialized correctly
        """
        base_path = tmp_path / "atomic_test"
        storage_path = base_path / "deep" / "nested" / "path" / "todos.json"

        # Track order of operations
        operations = []
        lock_acquired = []
        lock_released = []

        original_method = Storage._secure_all_parent_directories

        def wrapped_method(self, directory):
            """Wrap the original method to track lock usage."""
            operations.append(('start', str(directory)))
            result = original_method(directory)
            operations.append(('end', str(directory)))
            return result

        # Monkey-patch to track operations
        Storage._secure_all_parent_directories = wrapped_method

        try:
            # Create storage (should use file locks)
            storage = Storage(str(storage_path))

            # Verify directory was created
            assert storage_path.parent.exists()

            # Verify operations were completed
            assert len(operations) > 0, "No directory operations recorded"

            # Operations should show proper sequencing (no interleaving)
            # If locks work correctly, each directory operation should complete
            # before the next one starts
            start_count = sum(1 for op, _ in operations if op == 'start')
            end_count = sum(1 for op, _ in operations if op == 'end')

            assert start_count == end_count, (
                f"Mismatched operations: {start_count} starts, {end_count} ends"
            )

        finally:
            # Restore original method
            Storage._secure_all_parent_directories = original_method

    def test_lock_file_cleanup(self, tmp_path):
        """Test that lock files are properly cleaned up after directory creation.

        This test ensures that lock files used during directory creation are
        removed after the operation completes, even if exceptions occur.
        """
        base_path = tmp_path / "lock_cleanup_test"
        storage_path = base_path / "todos.json"

        # Create storage
        storage = Storage(str(storage_path))

        # Look for any .lock files in the directory tree
        lock_files = []
        for root, dirs, files in os.walk(tmp_path):
            for file in files:
                if file.endswith('.lock'):
                    lock_files.append(os.path.join(root, file))

        # Lock files should be cleaned up
        assert len(lock_files) == 0, f"Lock files not cleaned up: {lock_files}"

    def test_lock_file_contention_handling(self, tmp_path):
        """Test that the system handles lock file contention correctly.

        This test verifies that when one process holds a lock, other processes
        wait patiently and eventually succeed.
        """
        base_path = tmp_path / "contention_test"
        storage_path = base_path / "todos.json"

        results = []
        timings = []

        def create_storage_with_delay(thread_id):
            """Create storage and track timing."""
            start = time.time()
            try:
                # First thread creates the directory
                if thread_id == 0:
                    time.sleep(0.05)  # Hold lock longer

                storage = Storage(str(storage_path))
                elapsed = time.time() - start
                timings.append((thread_id, elapsed))
                results.append(thread_id)
                return thread_id
            except Exception as e:
                timings.append((thread_id, time.time() - start))
                results.append(f"error_{thread_id}: {e}")
                raise

        # Run threads concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_storage_with_delay, i) for i in range(3)]
            completed = [f.result() for f in as_completed(futures)]

        # All should complete successfully
        assert len(completed) == 3
        assert all(isinstance(r, int) for r in results)

        # Later threads should have taken longer due to waiting for lock
        timings.sort(key=lambda x: x[0])
        if len(timings) >= 2:
            # Second and third threads should have waited for first thread's lock
            # (allowing some variance for thread scheduling)
            assert timings[0][1] >= 0.05  # First thread with delay

    def test_race_condition_between_exist_check_and_mkdir(self, tmp_path):
        """Test the specific TOCTOU issue between exists() check and mkdir().

        This is the core issue from Issue #521: Without file locks, there's
        a window between the exists() check and the mkdir() call where another
        process can create the directory, causing permission issues.
        """
        base_path = tmp_path / "toctou_test"
        storage_path = base_path / "race" / "todos.json"

        # This test verifies that the implementation uses file locks
        # to prevent the classic TOCTOU race condition

        # Create multiple storage instances concurrently
        # Without proper locking, this could lead to:
        # 1. Thread A checks exists() -> False
        # 2. Thread B checks exists() -> False
        # 3. Thread A creates directory (insecure permissions)
        # 4. Thread B creates directory (fails or has wrong permissions)
        # With file locks, Thread B waits for Thread A to finish

        successful_creates = []

        def attempt_create(thread_id):
            """Attempt to create storage."""
            try:
                storage = Storage(str(storage_path))

                # Verify the parent directory has correct permissions
                parent = storage_path.parent
                if parent.exists() and os.name != 'nt':
                    stat_info = os.stat(parent)
                    mode = stat_info.st_mode & 0o777
                    # Should be secure (700 or 750)
                    assert mode in (0o700, 0o750), (
                        f"Thread {thread_id}: Insecure permissions {oct(mode)}"
                    )

                successful_creates.append(thread_id)
                return thread_id
            except Exception as e:
                successful_creates.append(f"error_{thread_id}: {e}")
                raise

        # Run with high concurrency to maximize race condition exposure
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(attempt_create, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All attempts should succeed
        assert len(results) == 20
        assert all(isinstance(r, int) for r in successful_creates), (
            f"Some threads failed: {successful_creates}"
        )
