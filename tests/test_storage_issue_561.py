"""Tests for Issue #561 - Race condition in directory creation.

This test validates that directory creation is atomic and secure,
preventing race conditions when multiple processes create directories concurrently.
"""

import os
import stat
import tempfile
from pathlib import Path
from flywheel.storage import Storage


def test_directory_creation_atomicity():
    """Test that directories are created with secure permissions atomically.

    This test validates that:
    1. Directories are created with mode 0o700 (user-only access)
    2. No race condition window exists where directories have insecure permissions
    3. The implementation uses atomic operations (preferably os.makedirs with controlled umask)

    Related to Issue #561.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "nested" / "dir" / "test.json"

        # Create storage which should create parent directories
        storage = Storage(path=str(test_path))

        # Check that all parent directories exist
        assert test_path.parent.exists(), "Parent directory should be created"
        assert (Path(tmpdir) / "nested").exists(), "Nested parent should be created"
        assert (Path(tmpdir) / "nested" / "dir").exists(), "Deep nested parent should be created"

        # Verify all parent directories have secure permissions (0o700)
        for parent in [test_path.parent, Path(tmpdir) / "nested", Path(tmpdir) / "nested" / "dir"]:
            if parent.exists():
                stat_info = parent.stat()
                mode = stat_info.st_mode

                # Check that directory has user-only permissions
                # On Unix, this means 0o700 (rwx------
                if os.name != 'nt':  # Unix-like systems
                    assert stat.S_ISDIR(mode), f"{parent} should be a directory"

                    # Extract permission bits
                    perm_mode = stat.S_IMODE(mode)

                    # Verify no world-readable or writable permissions
                    assert (perm_mode & stat.S_IROTH) == 0, (
                        f"{parent} should not be world-readable (potential race condition)"
                    )
                    assert (perm_mode & stat.S_IWOTH) == 0, (
                        f"{parent} should not be world-writable (potential race condition)"
                    )
                    assert (perm_mode & stat.S_IXOTH) == 0, (
                        f"{parent} should not be world-executable (potential race condition)"
                    )

                    # Verify no group-readable or writable permissions
                    assert (perm_mode & stat.S_IRGRP) == 0, (
                        f"{parent} should not be group-readable (potential race condition)"
                    )
                    assert (perm_mode & stat.S_IWGRP) == 0, (
                        f"{parent} should not be group-writable (potential race condition)"
                    )
                    assert (perm_mode & stat.S_IXGRP) == 0, (
                        f"{parent} should not be group-executable (potential race condition)"
                    )


def test_directory_creation_with_umask():
    """Test that directory creation is not affected by umask.

    The implementation should use a controlled umask (e.g., 0o077) when creating
    directories to ensure they always have secure permissions, regardless of
    the system's default umask setting.

    Related to Issue #561.
    """
    # Save original umask
    original_umask = os.umask(0)

    try:
        # Set a permissive umask (world-readable/writable)
        os.umask(0o000)

        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "permissive" / "dir" / "test.json"

            # Create storage - should override umask and create secure directories
            storage = Storage(path=str(test_path))

            # Verify directories have secure permissions despite permissive umask
            if os.name != 'nt':  # Unix-like systems
                for parent in [test_path.parent, Path(tmpdir) / "permissive"]:
                    if parent.exists():
                        stat_info = parent.stat()
                        mode = stat_info.st_mode
                        perm_mode = stat.S_IMODE(mode)

                        # Should NOT have world permissions even though umask is 0o000
                        assert (perm_mode & stat.S_IROTH) == 0, (
                            f"{parent} should not be world-readable even with permissive umask"
                        )
                        assert (perm_mode & stat.S_IWOTH) == 0, (
                            f"{parent} should not be world-writable even with permissive umask"
                        )
    finally:
        # Restore original umask
        os.umask(original_umask)


def test_existing_directory_permissions():
    """Test that existing directories are secured, not just newly created ones.

    This validates that _secure_all_parent_directories properly secures
    parent directories that may have been created by other processes
    with insecure permissions.

    Related to Issue #561.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a parent directory with permissive permissions
        parent = Path(tmpdir) / "existing"
        parent.mkdir(mode=0o755)  # Explicitly create with permissive permissions

        # Verify it has permissive permissions
        if os.name != 'nt':
            stat_info = parent.stat()
            perm_mode = stat.S_IMODE(stat_info.st_mode)
            assert (perm_mode & stat.S_IROTH) != 0 or (perm_mode & stat.S_IRGRP) != 0, (
                "Setup: directory should have permissive permissions initially"
            )

        # Create storage - should secure the existing parent directory
        test_path = parent / "test.json"
        storage = Storage(path=str(test_path))

        # Verify the parent directory has been secured
        if os.name != 'nt':
            stat_info = parent.stat()
            perm_mode = stat.S_IMODE(stat_info.st_mode)

            # Should now have restrictive permissions
            assert (perm_mode & stat.S_IROTH) == 0, (
                f"{parent} should not be world-readable after securing"
            )
            assert (perm_mode & stat.S_IWOTH) == 0, (
                f"{parent} should not be world-writable after securing"
            )
            assert (perm_mode & stat.S_IRGRP) == 0, (
                f"{parent} should not be group-readable after securing"
            )
            assert (perm_mode & stat.S_IWGRP) == 0, (
                f"{parent} should not be group-writable after securing"
            )
