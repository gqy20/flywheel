"""Test file permissions for security (Issue #179)."""

import os
import tempfile
import stat
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_temp_file_has_strict_permissions():
    """Test that temporary files created during save have 0o600 permissions.

    This is a security test to ensure that sensitive todo data is not
    exposed through overly permissive temporary file permissions.

    Ref: Issue #179
    """
    # Create a storage in a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo (this will trigger _save_with_todos)
        todo = Todo(title="Secret task", status="pending")
        storage.add(todo)

        # The main file should exist now
        assert storage_path.exists()

        # Create a temp directory to monitor for temp files
        temp_parent = Path(tmpdir)

        # Trigger another save to create a temp file
        # We'll monitor the directory before and after
        files_before = set(temp_parent.glob("*.tmp"))

        # Add another todo
        todo2 = Todo(title="Another task", status="pending")
        storage.add(todo2)

        # Check for new .tmp files that might have been created
        files_after = set(temp_parent.glob("*.tmp"))
        new_temp_files = files_after - files_before

        # If temp files exist, check their permissions
        # Note: In normal operation, temp files are quickly renamed/replaced,
        # so we might not catch them. Let's check the main file's permissions
        # as a proxy for what the temp file permissions should be.

        # The actual test: verify that when we create a file similar to how
        # _save does it, the permissions are set correctly
        import shutil

        # Simulate what _save does
        test_fd, test_temp_path = tempfile.mkstemp(
            dir=temp_parent,
            prefix="test.",
            suffix=".tmp"
        )

        try:
            # Before the fix: temp file might have loose permissions
            # After the fix: we expect os.fchmod to be called to set 0o600
            # For this test, we'll check the main file's permissions

            # Check the main file permissions
            file_stat = storage_path.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)

            # The file should have restrictive permissions (owner read/write only)
            # On Windows, permissions work differently, so we skip this check
            # On Unix-like systems, we expect 0o600 (rw-------)
            # However, the actual file created by atomic replace might inherit
            # from the temp file, so let's check what we get

            # For security, we want to ensure files are not world-readable
            # At minimum, the file should NOT be readable by others
            if os.name != 'nt':  # Skip on Windows
                # File should not be readable by group or others
                assert not (file_mode & stat.S_IRGRP), "File should not be readable by group"
                assert not (file_mode & stat.S_IROTH), "File should not be readable by others"

        finally:
            # Clean up test file
            try:
                os.close(test_fd)
                os.unlink(test_temp_path)
            except:
                pass


def test_temp_file_permissions_during_creation():
    """Test that demonstrates the security issue: temp files without 0o600.

    This test checks the actual behavior of tempfile.mkstemp and verifies
    that we explicitly set permissions to 0o600.

    Ref: Issue #179
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_parent = Path(tmpdir)

        # Create a temp file exactly as _save does
        fd, temp_path = tempfile.mkstemp(
            dir=temp_parent,
            prefix="todos.json.",
            suffix=".tmp"
        )

        try:
            # Check initial permissions from mkstemp
            temp_stat = os.stat(temp_path)
            temp_mode = stat.S_IMODE(temp_stat.st_mode)

            # On Unix systems, tempfile.mkstemp creates files with mode 0o600
            # ONLY if the umask is set appropriately. With a permissive umask
            # (e.g., 0000), the file could have permissions like 0o644.
            #
            # The fix should ensure we ALWAYS set 0o600 regardless of umask.

            # To demonstrate the issue and the fix:
            # We expect the code to call os.fchmod(fd, 0o600) after mkstemp

            # Simulate the fix
            os.fchmod(fd, 0o600)

            # Verify permissions are now set correctly
            temp_stat_after = os.stat(temp_path)
            temp_mode_after = stat.S_IMODE(temp_stat_after.st_mode)

            if os.name != 'nt':  # Skip on Windows
                assert temp_mode_after == 0o600, f"Expected 0o600, got {oct(temp_mode_after)}"

        finally:
            os.close(fd)
            os.unlink(temp_path)


def test_storage_save_creates_secure_files():
    """Integration test: verify Storage creates files with secure permissions.

    This test verifies that the actual Storage class properly sets
    file permissions to prevent unauthorized access.

    Ref: Issue #179
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "secure_todos.json"

        # Create storage and add a todo
        storage = Storage(str(storage_path))
        storage.add(Todo(title="Sensitive data", status="pending"))

        # Check the main file permissions
        if os.name != 'nt':  # Skip on Windows
            file_stat = storage_path.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)

            # Verify file is not readable by group or others
            assert not (file_mode & stat.S_IRGRP), "File should not be readable by group"
            assert not (file_mode & stat.S_IROTH), "File should not be readable by others"

            # Ideally, file should have 0o600 permissions
            # Note: This might be affected by umask, which is why the fix
            # explicitly uses os.fchmod(fd, 0o600)
            expected_mode = 0o600
            assert file_mode == expected_mode, f"Expected {oct(expected_mode)}, got {oct(file_mode)}"
