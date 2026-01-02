"""Test secure directory creation with umask (Issue #474).

This test verifies that directories are created with secure permissions
regardless of the umask setting. The issue is that while mode=0o700 is
set in mkdir(), the effective permissions are affected by the user's umask.

If the umask is loose (e.g., 0o022), the directory might be created with
0o755 permissions before _secure_directory() fixes it, creating a small
window of vulnerability.

The fix should use umask temporary restriction during directory creation.
"""

import os
import tempfile
import stat
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_directory_creation_respects_umask_on_unix():
    """Test that directories are created securely even with permissive umask.

    This test demonstrates the security issue: when umask is 0o022,
    mkdir(mode=0o700) creates a directory with 0o755 permissions instead
    of 0o700, creating a window of vulnerability.

    The fix should temporarily restrict umask during directory creation.

    Ref: Issue #474
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save original umask
        original_umask = os.umask(0)

        try:
            # Set a permissive umask (0o022 = group write, others write disabled)
            # This will make mkdir(mode=0o700) create directories with 0o755
            os.umask(0o022)

            # Create a storage instance with a nested path
            # This will trigger directory creation in _create_and_secure_directories
            storage_path = Path(tmpdir) / "subdir" / "todos.json"

            # Mock the umask during directory creation to test the fix
            # The fix should temporarily set umask to 0o077 during mkdir
            storage = Storage(str(storage_path))

            # Check that the parent directory was created with secure permissions
            parent_dir = storage_path.parent
            assert parent_dir.exists()

            parent_stat = parent_dir.stat()
            parent_mode = stat.S_IMODE(parent_stat.st_mode)

            # After the fix, the directory should have 0o700 permissions
            # even though umask was 0o022
            expected_mode = 0o700
            assert parent_mode == expected_mode, (
                f"Directory created with insecure permissions {oct(parent_mode)} "
                f"despite mode=0o700. Expected {oct(expected_mode)}. "
                f"This indicates the umask was not properly restricted during creation."
            )

        finally:
            # Restore original umask
            os.umask(original_umask)


def test_directory_permissions_after_creation():
    """Test that _secure_directory is called immediately after mkdir.

    This verifies the layered security approach:
    1. Create directory with mode=0o700 (which may be affected by umask)
    2. Immediately call _secure_directory to fix permissions if needed

    Ref: Issue #474
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save original umask
        original_umask = os.umask(0)

        try:
            # Set a very permissive umask
            os.umask(0o000)

            # Create storage
            storage_path = Path(tmpdir) / "test" / "todos.json"
            storage = Storage(str(storage_path))

            # Verify the directory exists and is secure
            parent_dir = storage_path.parent
            parent_stat = parent_dir.stat()
            parent_mode = stat.S_IMODE(parent_stat.st_mode)

            # The directory must be 0o700 (owner-only access)
            assert parent_mode == 0o700, (
                f"Directory has insecure permissions {oct(parent_mode)}. "
                f"Expected 0o700. Even with umask=0o000, the directory "
                f"should be secured by _secure_directory."
            )

        finally:
            # Restore original umask
            os.umask(original_umask)


def test_umask_does_not_affect_directory_security():
    """Integration test: verify various umask settings don't compromise security.

    This test creates multiple directories with different umask settings
    to ensure the security fix works in all cases.

    Ref: Issue #474
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        original_umask = os.umask(0)

        try:
            # Test with various umask values
            test_umasks = [0o000, 0o022, 0o027, 0o077]

            for test_umask in test_umasks:
                os.umask(test_umask)

                # Create a unique storage path for each umask
                subdir_name = f"umask_{oct(test_umask)}"
                storage_path = Path(tmpdir) / subdir_name / "todos.json"

                # Create storage
                storage = Storage(str(storage_path))

                # Verify directory permissions are secure
                parent_dir = storage_path.parent
                parent_stat = parent_dir.stat()
                parent_mode = stat.S_IMODE(parent_stat.st_mode)

                # Regardless of umask, directory should be 0o700
                assert parent_mode == 0o700, (
                    f"With umask={oct(test_umask)}, directory has "
                    f"permissions {oct(parent_mode)} instead of 0o700. "
                    f"This indicates a security vulnerability."
                )

        finally:
            os.umask(original_umask)
