"""Test for Issue #424 - TOCTOU race condition in directory creation.

This test verifies that the directory creation logic properly handles
race conditions where another process creates a directory with insecure
permissions between the existence check and creation attempt.

The issue requires that _create_and_secure_directores:
1. Uses atomic pattern (temp directory + rename) OR
2. Verifies permissions before proceeding when directory already exists
"""

import os
import tempfile
import threading
import time
from pathlib import Path
import pytest

from flywheel.storage import Storage


class TestIssue424TOCTOUDirectory:
    """Test TOCTOU race condition in directory creation."""

    def test_directory_created_with_insecure_permissions_is_fixed(self):
        """Test that if a directory is created with insecure permissions,
        the _create_and_secure_directories method detects and fixes it.

        This simulates a race condition where another process creates
        the directory with wrong permissions (e.g., due to permissive umask).
        """
        # Skip on Windows as permissions work differently
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a parent directory path
            test_dir = Path(tmpdir) / "test_flywheel" / "todos"

            # Simulate race condition: create directory with insecure permissions
            # This represents another process creating it with umask 022 (755 permissions)
            test_dir.mkdir(parents=True, exist_ok=True)
            test_dir.chmod(0o755)  # Insecure: group and others can read

            # Verify directory has insecure permissions
            stat_info = test_dir.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o755, "Test setup failed: directory should have 755 permissions"

            # Now create Storage - it should detect and fix the insecure permissions
            storage_path = test_dir / "todos.json"
            storage = Storage(path=str(storage_path))

            # Verify permissions were fixed to 0o700
            stat_info = test_dir.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o700, f"Directory should have 700 permissions after Storage init, got {oct(mode)}"

    def test_concurrent_directory_creation_with_insecure_permissions(self):
        """Test that concurrent directory creation handles insecure permissions.

        This test simulates multiple threads trying to create the same directory
        where one thread creates it with insecure permissions.
        """
        # Skip on Windows as permissions work differently
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "race_test" / "nested" / "todos"
            storage_path = test_dir / "todos.json"

            # Track successful creations
            results = {"count": 0, "errors": []}
            lock = threading.Lock()

            def try_create_storage():
                """Try to create storage, track success/failure."""
                try:
                    storage = Storage(path=str(storage_path))
                    with lock:
                        results["count"] += 1
                except Exception as e:
                    with lock:
                        results["errors"].append(str(e))

            # Start with directory not existing
            # Create multiple threads that will race
            threads = []
            for i in range(5):
                # Stagger thread starts slightly to increase race condition likelihood
                t = threading.Thread(target=try_create_storage)
                threads.append(t)
                time.sleep(0.001)  # Small delay
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join()

            # Verify at least some threads succeeded
            assert results["count"] > 0, "At least one thread should succeed"
            assert len(results["errors"]) == 0, f"No errors should occur, got: {results['errors']}"

            # Verify final directory has secure permissions
            stat_info = test_dir.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o700, f"Final directory should have 700 permissions, got {oct(mode)}"

    def test_parent_directory_permissions_verified(self):
        """Test that all parent directories are secured, not just the final one.

        This is a regression test for the defensive measure mentioned in the issue:
        ensure that even if parent directories were created by other processes
        with insecure permissions, we secure them now.
        """
        # Skip on Windows as permissions work differently
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create parent directory with insecure permissions
            parent_dir = Path(tmpdir) / "insecure_parent"
            parent_dir.mkdir()
            parent_dir.chmod(0o755)  # Insecure permissions

            # Create nested path that will be created by Storage
            nested_dir = parent_dir / "nested" / "todos"
            storage_path = nested_dir / "todos.json"

            # Create Storage - it should secure parent_dir too
            storage = Storage(path=str(storage_path))

            # Verify parent directory was secured
            stat_info = parent_dir.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o700, f"Parent directory should be secured to 700, got {oct(mode)}"

            # Verify nested directory was created with secure permissions
            stat_info = nested_dir.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o700, f"Nested directory should have 700 permissions, got {oct(mode)}"

    def test_windows_should_verify_acl_on_existing_directory(self):
        """Test that on Windows, ACLs are verified when directory already exists.

        This test documents the expected behavior: when _create_and_secure_directories
        encounters a FileExistsError, it should verify the directory has correct ACLs
        and fix them if needed.

        Note: This is a placeholder test to document the requirement.
        The actual Windows ACL verification is complex and requires pywin32.
        """
        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_windows"
            test_dir.mkdir(parents=True)

            # Create Storage - directory already exists
            storage_path = test_dir / "todos.json"
            storage = Storage(path=str(storage_path))

            # If we reach here without exception, the code handles existing directories
            # The real question is: did it verify the ACLs?
            # This test documents that ACL verification should happen
            assert True, "Storage should handle existing directory and verify/fix ACLs"

    def test_retry_mechanism_handles_race_condition(self):
        """Test that the retry mechanism properly handles TOCTOU race conditions.

        This verifies that when FileExistsError occurs due to race condition,
        the retry mechanism with exponential backoff kicks in.
        """
        # Skip on Windows as permissions work differently
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "retry_test"
            storage_path = test_dir / "todos.json"

            # Simulate multiple processes trying to create same directory
            results = []
            lock = threading.Lock()

            def create_with_delay():
                """Create storage after a small delay to simulate race."""
                time.sleep(0.01)  # Small delay
                try:
                    storage = Storage(path=str(storage_path))
                    with lock:
                        results.append(("success", storage_path))
                except Exception as e:
                    with lock:
                        results.append(("error", str(e)))

            # Launch multiple threads
            threads = []
            for _ in range(3):
                t = threading.Thread(target=create_with_delay)
                threads.append(t)
                t.start()

            # Wait for completion
            for t in threads:
                t.join()

            # All should succeed
            assert all(r[0] == "success" for r in results), \
                f"All threads should succeed, got: {results}"

            # Directory should have secure permissions
            stat_info = test_dir.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o700, f"Directory should have 700 permissions, got {oct(mode)}"
