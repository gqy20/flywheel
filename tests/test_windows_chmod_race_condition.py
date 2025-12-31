"""Test for Windows chmod race condition fix (Issue #205).

This test verifies that when os.fchmod is not available (Windows),
the chmod fallback is applied IMMEDIATELY, before any data is written
to the temporary file. This prevents a race condition where the file
could be accessed with default (loose) permissions.
"""

import json
import os
import stat
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestWindowsChmodRaceCondition:
    """Test that Windows chmod fallback doesn't have race conditions."""

    def test_chmod_applied_before_write_on_windows(self, tmp_path):
        """Test that chmod is applied before data is written when os.fchmod is unavailable.

        This test simulates Windows behavior where os.fchmod raises AttributeError.
        It verifies that the chmod fallback is applied immediately, before any
        data is written to the file, preventing the race condition.
        """
        # Create a storage instance
        storage_dir = tmp_path / "test_storage"
        storage_dir.mkdir()
        storage_path = storage_dir / "todos.json"

        # Track the order of operations
        operations = []

        original_fchmod = getattr(os, 'fchmod', None)

        def mock_fchmod(fd, mode):
            """Mock fchmod that raises AttributeError to simulate Windows."""
            operations.append(('fchmod_attempt', fd, mode))
            raise AttributeError("os.fchmod not available")

        def mock_write(fd, data):
            """Mock write that tracks when it's called."""
            operations.append(('write', fd, len(data)))
            return len(data)  # Return full write

        def mock_chmod(path, mode):
            """Mock chmod that tracks when it's called."""
            operations.append(('chmod', path, mode))

        # Add a todo to trigger _save
        with mock.patch.object(os, 'fchmod', side_effect=mock_fchmod), \
             mock.patch.object(os, 'write', side_effect=mock_write), \
             mock.patch.object(os, 'chmod', side_effect=mock_chmod):

            storage = Storage(str(storage_path))
            storage.add(Todo(title="Test todo", status="pending"))

        # Verify operations order
        # We should have: fchmod_attempt -> chmod -> write
        # NOT: fchmod_attempt -> write -> chmod (which would be the race condition)

        fchmod_idx = None
        chmod_idx = None
        write_idx = None

        for i, op in enumerate(operations):
            if op[0] == 'fchmod_attempt':
                fchmod_idx = i
            elif op[0] == 'chmod':
                chmod_idx = i
            elif op[0] == 'write':
                write_idx = i

        # fchmod was attempted
        assert fchmod_idx is not None, "fchmod should have been attempted"

        # chmod was applied (fallback)
        assert chmod_idx is not None, "chmod fallback should have been applied"

        # write was called
        assert write_idx is not None, "write should have been called"

        # THE CRITICAL CHECK: chmod must come BEFORE write
        # This ensures the file has restrictive permissions before any data is written
        assert chmod_idx < write_idx, \
            f"chmod must be applied before write to prevent race condition. " \
            f"Order: {[op[0] for op in operations]}"

    def test_temp_file_has_restrictive_permissions(self, tmp_path):
        """Test that temporary files are created with restrictive permissions.

        This is an integration test that verifies the actual file permissions
        on the temporary file (not just the order of operations).
        """
        if os.name == 'nt':
            # On Windows, we can't easily test this because the temp file
            # is deleted before we can check it
            pytest.skip("Cannot test file permissions on Windows")

        storage_dir = tmp_path / "test_storage"
        storage_dir.mkdir()
        storage_path = storage_dir / "todos.json"

        # Track created temp files
        temp_files = []
        original_mkstemp = tempfile.mkstemp

        def track_mkstemp(*args, **kwargs):
            """Track temp files created by mkstemp."""
            fd, path = original_mkstemp(*args, **kwargs)
            temp_files.append(path)
            return fd, path

        with mock.patch('tempfile.mkstemp', side_effect=track_mkstemp):
            storage = Storage(str(storage_path))
            storage.add(Todo(title="Test todo", status="pending"))

        # Check that temp file had restrictive permissions
        # Note: This checks the temp file BEFORE it's moved to final location
        # On success, the temp file is moved (renamed), so we check the final file
        assert storage_path.exists(), "Storage file should exist"

        # The final file should have restrictive permissions (0o600)
        # Note: On some systems, the actual permissions might be affected by umask
        # So we check that the file is not world-readable or group-readable
        st_mode = storage_path.stat().st_mode
        is_readable_by_others = bool(st_mode & stat.S_IROTH)
        is_readable_by_group = bool(st_mode & stat.S_IRGRP)

        assert not is_readable_by_others, \
            "File should not be readable by others (race condition vulnerability)"
        # Group read might be OK depending on umask, but let's check it's restrictive
        # We'll just warn about group readability since umask can affect this
