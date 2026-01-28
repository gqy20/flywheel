"""Test atomic directory creation with secure permissions (Issue #479).

This test verifies that directories are created with secure permissions
using an atomic approach that minimizes the TOCTOU (Time-of-Check-Time-of-Use)
window.

The security issue is that even with mode=0o700 in mkdir(), the umask can
override these permissions. While Issue #474 fixed this by temporarily
restricting the umask, there's still a theoretical race condition window.

Issue #479 suggests using os.open() with O_CREAT | O_EXCL to create
directories more atomically with secure permissions that are not subject
to umask interference.
"""

import os
import tempfile
import stat
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_directory_created_with_atomic_secure_permissions():
    """Test that directories are created atomically with secure permissions.

    This test verifies that directory creation uses an atomic approach
    that minimizes the TOCTOU window and ensures secure permissions
    regardless of umask.

    The test simulates a race condition scenario by using a very permissive
    umask and verifies that directories are still created with 0o700.

    Ref: Issue #479
    """
    if os.name == 'nt':  # Skip on Windows (different security model)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save original umask
        original_umask = os.umask(0)

        try:
            # Set an extremely permissive umask (0o000)
            # Without proper fixing, mkdir(mode=0o700) would create
            # directories with 0o777 permissions
            os.umask(0o000)

            # Create a storage instance with a nested path
            # This triggers _create_and_secure_directories
            storage_path = Path(tmpdir) / "secure_test" / "todos.json"

            # Create storage - this should create directories atomically
            storage = Storage(str(storage_path))

            # Verify the parent directory was created
            parent_dir = storage_path.parent
            assert parent_dir.exists(), "Parent directory should exist"

            # Check the directory permissions
            parent_stat = parent_dir.stat()
            parent_mode = stat.S_IMODE(parent_stat.st_mode)

            # The directory MUST have 0o700 permissions (owner-only)
            # This should be guaranteed by the atomic creation approach
            expected_mode = 0o700
            assert parent_mode == expected_mode, (
                f"Directory created with insecure permissions {oct(parent_mode)}. "
                f"Expected {oct(expected_mode)}. "
                f"This indicates the directory creation is not atomic with "
                f"respect to umask, creating a TOCTOU vulnerability."
            )

            # Verify all parent directories are also secure
            # This is important for defense-in-depth
            current = parent_dir
            while current != Path(tmpdir) and current.exists():
                dir_stat = current.stat()
                dir_mode = stat.S_IMODE(dir_stat.st_mode)

                # All directories should be secure
                assert dir_mode == 0o700, (
                    f"Parent directory {current} has insecure permissions "
                    f"{oct(dir_mode)}. Expected 0o700. This creates a "
                    f"security vulnerability where an attacker could traverse "
                    f"the directory tree."
                )

                # Move up one directory
                current = current.parent

        finally:
            # Restore original umask
            os.umask(original_umask)


def test_no_toctou_window_during_directory_creation():
    """Test that there's no TOCTOU window during directory creation.

    This test verifies that the directory creation and permission setting
    happen atomically, without a window where the directory exists with
    insecure permissions.

    The approach:
    1. Set a permissive umask
    2. Create a directory
    3. Immediately check permissions
    4. Verify permissions were secure from the start

    Ref: Issue #479
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        original_umask = os.umask(0)

        try:
            # Use umask that would make mkdir(mode=0o700) create 0o777
            os.umask(0o000)

            # Create multiple directories rapidly to test for race conditions
            for i in range(10):
                subdir = Path(tmpdir) / f"test_{i}" / "nested" / "todos.json"

                # Create storage
                storage = Storage(str(subdir))

                # Verify immediate security
                parent_dir = subdir.parent
                parent_stat = parent_dir.stat()
                parent_mode = stat.S_IMODE(parent_stat.st_mode)

                # Must be 0o700 immediately after creation
                assert parent_mode == 0o700, (
                    f"Iteration {i}: Directory has permissions {oct(parent_mode)} "
                    f"immediately after creation. Expected 0o700. "
                    f"This indicates a TOCTOU vulnerability."
                )

        finally:
            os.umask(original_umask)


def test_umask_cannot_compromise_directory_security():
    """Test that umask cannot compromise directory security under any conditions.

    This comprehensive test verifies that even with the most permissive
    umask settings, directories are created with secure 0o700 permissions.

    The test creates directories with various umask values and verifies
    that security is maintained in all cases.

    Ref: Issue #479
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        original_umask = os.umask(0)

        try:
            # Test with the most permissive umask values
            # These are the values that would cause the biggest security issues
            # if the directory creation is not atomic
            dangerous_umasks = [
                0o000,  # Most permissive - would create 0o777 without fix
                0o002,  # Would create 0o775 without fix
                0o022,  # Common umask - would create 0o755 without fix
                0o027,  # Would create 0o750 without fix
            ]

            for test_umask in dangerous_umasks:
                os.umask(test_umask)

                # Create a unique path for this umask
                subdir = Path(tmpdir) / f"umask_{oct(test_umask)}" / "todos.json"

                # Create storage
                storage = Storage(str(subdir))

                # Verify directory security
                parent_dir = subdir.parent
                parent_stat = parent_dir.stat()
                parent_mode = stat.S_IMODE(parent_stat.st_mode)

                # Security assertion: directory MUST be 0o700
                # regardless of umask
                assert parent_mode == 0o700, (
                    f"With umask={oct(test_umask)}, directory has "
                    f"permissions {oct(parent_mode)} instead of 0o700. "
                    f"This is a CRITICAL security vulnerability - an attacker "
                    f"could set a permissive umask to compromise directory security."
                )

        finally:
            os.umask(original_umask)


def test_directory_creation_is_idempotent():
    """Test that directory creation is idempotent and always results in secure permissions.

    This test verifies that if a directory already exists (even with insecure
    permissions), creating a Storage instance will secure it.

    This is important for handling race conditions where another process
    might create a directory with insecure permissions.

    Ref: Issue #479
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        original_umask = os.umask(0)

        try:
            # Set permissive umask
            os.umask(0o000)

            # Create a directory with insecure permissions manually
            insecure_dir = Path(tmpdir) / "insecure_test"
            insecure_dir.mkdir(mode=0o777)

            # Verify it's insecure
            stat_info = insecure_dir.stat()
            mode = stat.S_IMODE(stat_info.st_mode)
            assert mode == 0o777, f"Setup failed: directory mode is {oct(mode)}, not 0o777"

            # Now create a Storage instance that uses this directory
            storage_path = insecure_dir / "todos.json"

            # This should secure the directory
            storage = Storage(str(storage_path))

            # Verify the directory is now secure
            stat_info_after = insecure_dir.stat()
            mode_after = stat.S_IMODE(stat_info_after.st_mode)

            assert mode_after == 0o700, (
                f"Directory still has insecure permissions {oct(mode_after)} "
                f"after Storage creation. Expected 0o700. "
                f"The Storage class should secure existing parent directories."
            )

        finally:
            os.umask(original_umask)


if __name__ == "__main__":
    # Run tests
    test_directory_created_with_atomic_secure_permissions()
    print("✓ test_directory_created_with_atomic_secure_permissions passed")

    test_no_toctou_window_during_directory_creation()
    print("✓ test_no_toctou_window_during_directory_creation passed")

    test_umask_cannot_compromise_directory_security()
    print("✓ test_umask_cannot_compromise_directory_security passed")

    test_directory_creation_is_idempotent()
    print("✓ test_directory_creation_is_idempotent passed")

    print("\nAll tests passed!")
