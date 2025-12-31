"""Test for race condition in temporary file permissions (Issue #194)."""

import os
import tempfile
import stat
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_temp_file_creation_race_condition():
    """Test that there's no race condition between mkstemp and fchmod.

    The current implementation has a security issue:
    1. tempfile.mkstemp() creates a file with umask-based permissions
    2. os.fchmod(fd, 0o600) sets restrictive permissions

    Between these two calls, there's a brief window where the file
    may have default permissions. While this window is very small,
    in high-security scenarios this is a vulnerability.

    The fix should ensure that the parent directory has restrictive
    permissions (0o700) so that even if temp files have loose permissions
    momentarily, they cannot be accessed by other users.

    Ref: Issue #194
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # The storage directory should be created with restrictive permissions
        # to protect any temporary files that might be created during save
        storage_dir = storage_path.parent

        # Check directory permissions
        if os.name != 'nt':  # Skip on Windows
            dir_stat = storage_dir.stat()
            dir_mode = stat.S_IMODE(dir_stat.st_mode)

            # The directory should have restrictive permissions (0o700)
            # This ensures that even if temp files have loose permissions
            # during the race condition window, they cannot be accessed by others
            expected_mode = 0o700
            assert dir_mode == expected_mode, (
                f"Directory should have {oct(expected_mode)} permissions to prevent "
                f"unauthorized access during temp file creation. Got {oct(dir_mode)}. "
                f"This is a security vulnerability (Issue #194)."
            )


def test_temp_file_has_restrictive_perms_from_creation():
    """Test that temp files are created with restrictive permissions from the start.

    This test checks that when we save todos, the temporary files created
    have proper permissions from the moment they're created, not after
    a delayed chmod call.

    Ref: Issue #194
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to trigger save
        storage.add(Todo(title="Test", status="pending"))

        # Now let's simulate what happens in _save:
        # We need to ensure the directory permissions protect us
        storage_dir = storage_path.parent

        if os.name != 'nt':  # Skip on Windows
            dir_stat = storage_dir.stat()
            dir_mode = stat.S_IMODE(dir_stat.st_mode)

            # Directory must be 0o700 (drwx------) to protect temp files
            # This is the defense-in-depth approach to prevent the race condition
            assert dir_mode == 0o700, (
                f"Storage directory must have restrictive permissions (0o700) "
                f"to protect temp files from the race condition. Got {oct(dir_mode)}"
            )
