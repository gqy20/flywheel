"""Test directory creation security (Issue #364).

This test verifies that directory creation happens with secure permissions
from the start, without a time window where default permissions could expose
the directory.

Issue #364: In `__init__`, directory creation (`mkdir`) happens before setting
permissions (`_secure_directory`), creating a security window where the directory
could have default permissions (e.g., 0755).
"""

import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import threading
import time

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_directory_created_with_secure_permissions():
    """Test that directory is created with secure permissions immediately.

    This test verifies that when Storage creates a directory, it does so
    with secure permissions from the start, without a race condition window
    where the directory could have overly permissive default permissions.

    Ref: Issue #364
    """
    if os.name == 'nt':  # Skip on Windows (uses ACLs instead)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a unique path for testing
        test_dir = Path(tmpdir) / "secure_test" / "todos.json"

        # Mock _secure_directory to capture when it's called
        original_secure = Storage._secure_directory
        secure_called_with = []

        def mock_secure(self, directory):
            """Mock that captures the directory argument and checks permissions."""
            # Check if directory exists at this point
            if directory.exists():
                dir_stat = directory.stat()
                dir_mode = stat.S_IMODE(dir_stat.st_mode)
                secure_called_with.append((str(directory), dir_mode))

            # Call the original to complete the test setup
            return original_secure(self, directory)

        with patch.object(Storage, '_secure_directory', mock_secure):
            # Create storage - this triggers directory creation
            storage = Storage(str(test_dir))

        # Verify the directory was created
        assert test_dir.parent.exists(), "Parent directory should be created"

        # Check that the directory exists
        assert test_dir.parent.exists()

        # Check final permissions are secure (0o700)
        dir_stat = test_dir.parent.stat()
        dir_mode = stat.S_IMODE(dir_stat.st_mode)
        assert dir_mode == 0o700, f"Directory should have 0o700 permissions, got {oct(dir_mode)}"


def test_no_permission_race_condition_during_creation():
    """Test that there's no race condition window during directory creation.

    This test attempts to detect if there's a time window where the directory
    exists with insecure permissions. It does this by checking permissions
    immediately after directory creation.

    Ref: Issue #364
    """
    if os.name == 'nt':  # Skip on Windows (uses ACLs instead)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "race_test" / "todos.json"

        # Track directory creation events
        creation_events = []
        original_mkdir = Path.mkdir

        def tracked_mkdir(self, *args, **kwargs):
            """Track mkdir calls and immediately check permissions."""
            result = original_mkdir(self, *args, **kwargs)
            # Immediately check permissions after creation
            if self.exists():
                dir_stat = self.stat()
                dir_mode = stat.S_IMODE(dir_stat.st_mode)
                creation_events.append({
                    'path': str(self),
                    'mode': dir_mode,
                    'time': time.time()
                })
            return result

        with patch.object(Path, 'mkdir', tracked_mkdir):
            # Create storage
            storage = Storage(str(test_dir))

        # Verify directory was created
        assert test_dir.parent.exists()

        # Check if there was a race condition
        # If directory was created with insecure permissions (e.g., 0755),
        # that's a security issue
        if creation_events:
            for event in creation_events:
                # The directory should NOT have been created with overly permissive permissions
                # We check that it wasn't created with world-readable permissions
                mode = event['mode']
                # If it was created with 0755 or similar, that's a problem
                if mode & stat.S_IROTH:  # World-readable
                    # This would indicate a security window
                    raise AssertionError(
                        f"Directory created with insecure permissions {oct(mode)} "
                        f"before _secure_directory was called (Issue #364)"
                    )


def test_directory_permissions_from_start():
    """Test that directory has secure permissions from the moment it's created.

    This is a more direct test: we verify that the directory creation mechanism
    ensures secure permissions immediately, not as a separate step.

    Ref: Issue #364
    """
    if os.name == 'nt':  # Skip on Windows (uses ACLs instead)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "immediate_test" / "todos.json"

        # Create storage
        storage = Storage(str(test_dir))

        # The directory should exist
        assert test_dir.parent.exists()

        # Check permissions are secure
        dir_stat = test_dir.parent.stat()
        dir_mode = stat.S_IMODE(dir_stat.st_mode)

        # Directory should have 0o700 (owner only)
        assert dir_mode == 0o700, (
            f"Directory should have secure 0o700 permissions immediately, "
            f"got {oct(dir_mode)}"
        )

        # Specifically, it should NOT be readable by others
        assert not (dir_mode & stat.S_IROTH), (
            "Directory should not be world-readable (Issue #364)"
        )
        assert not (dir_mode & stat.S_IRGRP), (
            "Directory should not be group-readable (Issue #364)"
        )


def test_mkdir_with_mode_parameter():
    """Test that directory is created with secure mode parameter.

    This test FAILS on the original code because it uses mkdir(parents=True, exist_ok=True)
    without a mode parameter, creating a directory with default permissions first.

    The test PASSES when the code is fixed to create the directory with
    secure permissions from the start.

    Ref: Issue #364
    """
    if os.name == 'nt':  # Skip on Windows (uses ACLs instead)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "mode_test" / "todos.json"

        # Track whether mkdir was called with a mode parameter
        mkdir_calls = []
        original_mkdir = Path.mkdir

        def tracked_mkdir(self, *args, **kwargs):
            """Track mkdir calls and their arguments."""
            mkdir_calls.append({
                'args': args,
                'kwargs': kwargs.copy(),
                'path': str(self)
            })
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, 'mkdir', tracked_mkdir):
            storage = Storage(str(test_dir))

        # Check if mkdir was called with a mode parameter
        # The original code calls: mkdir(parents=True, exist_ok=True)
        # The fixed code should call: mkdir(parents=True, exist_ok=True, mode=0o700)
        assert len(mkdir_calls) > 0, "mkdir should have been called"

        # Find the call that created the parent directory
        parent_created = False
        mode_used = None

        for call in mkdir_calls:
            if 'mode' in call['kwargs']:
                parent_created = True
                mode_used = call['kwargs']['mode']
                break

        # The test will FAIL until the code is fixed to pass mode=0o700
        assert parent_created, (
            "Directory should be created with mode parameter to ensure "
            "secure permissions from the start (Issue #364)"
        )

        assert mode_used == 0o700, (
            f"Directory should be created with mode=0o700 for security, "
            f"got mode={oct(mode_used) if mode_used else None} (Issue #364)"
        )
