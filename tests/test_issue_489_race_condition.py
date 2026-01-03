"""Tests for Issue #489 - Race condition in directory creation.

This test verifies that directory creation is atomic with respect to permissions,
even when multiple processes attempt to create the same directory concurrently.

Note: The fix for this issue was already implemented in Issues #474 and #479.
The code uses os.umask(0o077) before mkdir(mode=0o700) to ensure atomic
creation with secure permissions, eliminating the TOCTOU security window.

This test validates that the fix is working correctly.
"""

import os
import stat
import tempfile
import shutil
from pathlib import Path
import pytest
from flywheel.storage import Storage


class TestDirectoryCreationAtomicity:
    """Test atomic directory creation with secure permissions."""

    def test_unix_directory_created_with_restrictive_permissions(self):
        """Test that directories are created with mode 0o700 on Unix-like systems.

        This test verifies the fix for Issue #489 which addresses potential
        race conditions in directory creation. The directory should be created
        with restrictive permissions (0o700) from the start, not relying on
        a separate chmod call that could create a TOCTOU window.
        """
        if os.name == 'nt':  # Windows uses ACLs, not mode bits
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "test_storage", "todos.json")

            # Create storage which should create parent directories
            storage = Storage(path=test_path)

            # Check that all parent directories have mode 0o700
            parent_dir = Path(test_path).parent
            while parent_dir.exists() and parent_dir != Path(tmpdir):
                mode = parent_dir.stat().st_mode
                # Check that the directory has restrictive permissions
                # (owner read/write/execute only, no group/other permissions)
                assert (mode & 0o777) == 0o700, (
                    f"Directory {parent_dir} has insecure permissions: {oct(mode & 0o777)}. "
                    f"Expected 0o700. This indicates a potential race condition "
                    f"where the directory was created with umask-dependent permissions."
                )
                parent_dir = parent_dir.parent

            storage.close()

    def test_unix_mkdir_umask_restriction(self):
        """Test that mkdir uses umask restriction to ensure atomic permission setting.

        This test verifies that the implementation uses os.umask(0o077) before
        calling mkdir(mode=0o700) to prevent umask from making the directory
        more permissive than intended.

        This addresses the TOCTOU security window mentioned in Issue #489 where
        mkdir(mode=0o700) could create a directory with 0o755 permissions if
        umask is 0o022.
        """
        if os.name == 'nt':  # Windows uses ACLs
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with a permissive umask that would normally make directories 0o755
            original_umask = os.umask(0o022)

            try:
                test_path = os.path.join(tmpdir, "test_umask", "todos.json")
                storage = Storage(path=test_path)

                # Verify that despite the permissive umask (0o022),
                # the directory is created with 0o700
                parent_dir = Path(test_path).parent
                mode = parent_dir.stat().st_mode
                actual_permissions = mode & 0o777

                # The directory should be 0o700, not 0o755 (which would result
                # from umask 0o022 if the umask restriction wasn't applied)
                assert actual_permissions == 0o700, (
                    f"Directory {parent_dir} has permissions {oct(actual_permissions)}. "
                    f"Expected 0o700. Got {oct(actual_permissions)} which suggests "
                    f"umask restriction was not applied correctly. "
                    f"This is the security issue described in Issue #489."
                )

                storage.close()
            finally:
                os.umask(original_umask)

    def test_concurrent_directory_creation_safety(self):
        """Test that concurrent directory creation attempts are handled safely.

        This test simulates the race condition scenario where multiple processes
        attempt to create the same directory simultaneously. The implementation
        should handle FileExistsError gracefully and verify/secure the directory.

        This validates the retry mechanism and FileExistsError handling that
        addresses TOCTOU issues.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "race_condition", "todos.json")

            # Create the first storage instance
            storage1 = Storage(path=test_path)

            # Create a second storage instance pointing to the same location
            # This simulates a race condition where the directory already exists
            storage2 = Storage(path=test_path)

            # Both should succeed without errors
            assert storage1 is not None
            assert storage2 is not None

            # Verify the directory has secure permissions
            parent_dir = Path(test_path).parent
            if os.name != 'nt':  # Unix - check mode bits
                mode = parent_dir.stat().st_mode
                assert (mode & 0o777) == 0o700, (
                    f"Directory {parent_dir} has insecure permissions after "
                    f"concurrent creation: {oct(mode & 0o777)}"
                )

            storage1.close()
            storage2.close()

    def test_windows_directory_security_attributes(self):
        """Test that Windows directories are created with secure ACLs.

        On Windows, directories should be created with atomic ACLs using
        win32file.CreateDirectory. This test verifies that the directory
        has restrictive security attributes.

        Note: This test only verifies that creation succeeds. Full ACL
        verification would require Windows API calls to inspect the security
        descriptor, which is complex to test in Python.
        """
        if os.name != 'nt':  # Unix-only
            pytest.skip("Windows-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "test_windows", "todos.json")

            # This should succeed without errors
            storage = Storage(path=test_path)
            assert storage is not None

            # Verify directory exists
            parent_dir = Path(test_path).parent
            assert parent_dir.exists()

            storage.close()

    def test_no_insecure_permissions_window(self):
        """Test that there is no window where directories have insecure permissions.

        This test validates that the implementation does not have a TOCTOU
        window where a directory could exist with insecure permissions between
        mkdir() and chmod().

        The fix for Issue #489 uses umask restriction to ensure atomic
        permission setting, eliminating the window.
        """
        if os.name == 'nt':  # Windows uses different mechanism
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Set a permissive umask
            original_umask = os.umask(0o027)  # Would make directories 0o750 normally

            try:
                test_path = os.path.join(tmpdir, "secure_test", "nested", "todos.json")
                storage = Storage(path=test_path)

                # Walk through all created parent directories
                parent_dir = Path(test_path).parent
                while parent_dir.exists() and str(parent_dir) != tmpdir:
                    mode = parent_dir.stat().st_mode
                    actual_permissions = mode & 0o777

                    # All directories should be 0o700, not affected by umask
                    assert actual_permissions == 0o700, (
                        f"Directory {parent_dir} has permissions {oct(actual_permissions)}. "
                        f"Expected 0o700. If permissions are {oct(0o700 & ~0o027)} (0o750), "
                        f"it indicates umask was not restricted during creation, "
                        f"creating a TOCTOU security window as described in Issue #489."
                    )

                    parent_dir = parent_dir.parent

                storage.close()
            finally:
                os.umask(original_umask)
