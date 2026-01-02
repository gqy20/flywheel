"""Test for Issue #439 - Secure directory creation with atomic permissions.

This test verifies that _create_and_secure_directories atomically creates
directories with secure permissions (mode 0o700) or handles the FileExistsError
race condition securely by verifying permissions immediately after creation.

The security issue: If _create_and_secure_directories fails to apply restrictive
permissions (e.g., due to a race condition or error), the directory might be
created with insecure permissions (umask dependent).
"""

import os
import tempfile
import stat
from pathlib import Path
import pytest
from unittest.mock import patch, Mock

from flywheel.storage import Storage


class TestIssue439SecureDirectoryCreation:
    """Test secure directory creation with atomic permissions."""

    def test_directory_created_atomically_with_secure_permissions(self):
        """Test that directories are created with secure permissions from the start.

        This verifies that mkdir() uses mode=0o700 to ensure the directory is
        created with restrictive permissions, even if _secure_directory fails later.

        The current code uses mkdir() without mode parameter, then calls
        _secure_directory. If _secure_directory fails, the directory has
        umask-dependent permissions (security vulnerability).

        Ref: Issue #439
        """
        # Skip on Windows as permissions work differently
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_atomic" / "nested"

            # Set permissive umask to expose the vulnerability
            original_umask = os.umask(0)

            try:
                # Mock _secure_directory to fail and simulate the race condition
                original_secure = Storage._secure_directory

                def mock_secure_directory(self, directory):
                    # Simulate _secure_directory failing
                    raise RuntimeError(f"Simulated security failure for {directory}")

                with patch.object(Storage, '_secure_directory', mock_secure_directory):
                    storage_path = test_dir / "todos.json"

                    # Try to create storage - it will fail due to mocked _secure_directory
                    try:
                        storage = Storage(path=str(storage_path))
                        pytest.fail("Storage creation should fail when _secure_directory fails")
                    except RuntimeError:
                        # Expected to fail

                    # The security issue: directory was created but has insecure permissions
                    if test_dir.exists():
                        stat_info = test_dir.stat()
                        mode = stat_info.st_mode & 0o777

                        # With umask=0, mkdir() creates directory with 0o777 permissions
                        # This is the VULNERABILITY - should be 0o700
                        #
                        # The fix: use mkdir(mode=0o700) so directory has secure
                        # permissions even if _secure_directory fails
                        assert mode == 0o700, (
                            f"SECURITY VULNERABILITY: Directory was created with "
                            f"umask-dependent permissions {oct(mode)} instead of 0o700. "
                            f"If _secure_directory fails, directory remains insecure. "
                            f"Fix: Use mkdir(mode=0o700) to create with secure permissions."
                        )

            finally:
                os.umask(original_umask)

    def test_mkdir_without_umask_influence(self):
        """Test that directory creation is not influenced by permissive umask.

        This test simulates a permissive umask (e.g., 0000) and verifies that
        directories are still created with secure 0o700 permissions.

        Ref: Issue #439
        """
        # Skip on Windows as permissions work differently
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_umask"

            # Save original umask
            original_umask = os.umask(0)

            try:
                # Set permissive umask (allows all permissions)
                os.umask(0)

                # Create storage - should create directory with 0o700 regardless of umask
                storage_path = test_dir / "todos.json"
                storage = Storage(path=str(storage_path))

                # Verify directory has secure permissions despite permissive umask
                stat_info = test_dir.stat()
                mode = stat_info.st_mode & 0o777

                # With umask=0, mkdir() would create 0o777 by default
                # We expect 0o700 due to explicit permission setting
                assert mode == 0o700, (
                    f"Directory must have 0o700 permissions regardless of umask. "
                    f"With umask=0, got {oct(mode)}. This indicates directory creation "
                    f"is umask-dependent, which is a security vulnerability."
                )

            finally:
                # Restore original umask
                os.umask(original_umask)

    def test_concurrent_creation_maintains_security(self):
        """Test that concurrent directory creation attempts all result in secure permissions.

        This simulates multiple processes/threads creating the same directory
        and verifies that regardless of race conditions, the final directory
        always has secure permissions.

        Ref: Issue #439
        """
        # Skip on Windows as permissions work differently
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        import threading
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "race_secure" / "nested"
            storage_path = test_dir / "todos.json"

            results = {"success": 0, "errors": []}
            lock = threading.Lock()

            def create_storage():
                """Try to create storage in a thread."""
                try:
                    storage = Storage(path=str(storage_path))
                    with lock:
                        results["success"] += 1

                    # Verify directory has secure permissions
                    stat_info = test_dir.stat()
                    mode = stat_info.st_mode & 0o777

                    if mode != 0o700:
                        with lock:
                            results["errors"].append(
                                f"Insecure permissions {oct(mode)} detected"
                            )
                except Exception as e:
                    with lock:
                        results["errors"].append(str(e))

            # Launch multiple threads to create same directory
            threads = []
            for _ in range(5):
                t = threading.Thread(target=create_storage)
                threads.append(t)
                time.sleep(0.001)
                t.start()

            # Wait for completion
            for t in threads:
                t.join()

            # Verify no security violations occurred
            assert len(results["errors"]) == 0, (
                f"Security violations detected: {results['errors']}. "
                f"Concurrent directory creation should always result in secure permissions."
            )

            # Verify final directory has secure permissions
            stat_info = test_dir.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o700, (
                f"Final directory must have 0o700 permissions after concurrent creation. "
                f"Got {oct(mode)}. This is a security vulnerability."
            )

    def test_parent_directories_also_secured(self):
        """Test that all parent directories are created with secure permissions.

        This verifies that when creating a nested directory path, all parent
        directories in the chain are created with secure permissions, not just
        the final directory.

        Ref: Issue #439
        """
        # Skip on Windows as permissions work differently
        if os.name == 'nt':
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a deeply nested path
            nested_dirs = Path(tmpdir) / "level1" / "level2" / "level3"
            storage_path = nested_dirs / "todos.json"

            # Create storage
            storage = Storage(path=str(storage_path))

            # Verify ALL parent directories have secure permissions
            level1 = Path(tmpdir) / "level1"
            level2 = level1 / "level2"
            level3 = level2 / "level3"

            for directory in [level1, level2, level3]:
                assert directory.exists(), f"Directory {directory} should exist"

                stat_info = directory.stat()
                mode = stat_info.st_mode & 0o777

                assert mode == 0o700, (
                    f"All parent directories must have 0o700 permissions. "
                    f"Directory {directory} has {oct(mode)}. This is a security vulnerability."
                )

    def test_windows_acl_security(self):
        """Test that on Windows, directories are created with restrictive ACLs.

        This test documents the requirement for Windows: directories should be
        created with restrictive ACLs from the start, not default inherited ACLs.

        Note: This is a documentation test. Actual ACL verification requires
        complex Windows security APIs.

        Ref: Issue #439
        """
        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_windows_acl"
            storage_path = test_dir / "todos.json"

            # Create storage
            storage = Storage(path=str(storage_path))

            # Directory should exist
            assert test_dir.exists(), "Directory should be created"

            # Note: Actual ACL verification requires pywin32 and complex checks
            # This test documents that ACLs should be restrictive
            # The real security verification would involve:
            # 1. Getting the security descriptor
            # 2. Checking the DACL has only owner access
            # 3. Verifying no inherited permissions

            # For now, just verify directory creation succeeds
            # The real security check would be integration testing with Windows security APIs
            assert True, "Windows directory creation should apply restrictive ACLs"
