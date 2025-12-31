"""Tests for cross-platform directory permissions (Issue #226)."""

import os
import tempfile
import stat
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_directory_permissions_unix():
    """Test that storage directory has restrictive permissions on Unix-like systems."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test_storage/test.json"
        storage = Storage(path=storage_path)

        # Check directory permissions on Unix-like systems
        if os.name != 'nt':  # Unix-like
            dir_stat = storage.path.parent.stat()
            dir_mode = stat.S_IMODE(dir_stat.st_mode)

            # Directory should have 0o700 (rwx------) permissions
            # This ensures only the owner can access the directory
            assert dir_mode == 0o700, (
                f"Expected directory permissions 0o700, got {oct(dir_mode)}. "
                f"This is a security risk as other users may access sensitive data."
            )
        else:
            # On Windows, the directory should still be created
            # even though chmod is not applicable
            assert storage.path.parent.exists()


def test_file_permissions_restrictive():
    """Test that todo files have restrictive permissions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test.json"
        storage = Storage(path=storage_path)

        # Add a todo to trigger file creation
        storage.add(Todo(title="Test todo"))

        # Check file permissions
        if os.name != 'nt':  # Unix-like
            file_stat = storage.path.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)

            # File should have 0o600 (rw-------) permissions
            # This ensures only the owner can read/write the file
            assert file_mode == 0o600, (
                f"Expected file permissions 0o600, got {oct(file_mode)}. "
                f"This is a security risk as other users may read sensitive data."
            )
        else:
            # On Windows, the file should exist
            # Permissions are handled by Windows ACLs
            assert storage.path.exists()


def test_storage_initialization_creates_directory():
    """Test that Storage initialization creates the parent directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/nested/deep/storage.json"

        # Directory should not exist before Storage creation
        assert not Path(storage_path).parent.exists()

        # Create Storage
        storage = Storage(path=storage_path)

        # Directory should now exist
        assert storage.path.parent.exists()
        assert storage.path.parent.is_dir()
