"""Test Windows permission fallback mechanism (Issue #212).

This test verifies that the Windows permission fallback mechanism is working correctly.
The issue states that the os.fchmod fallback mechanism was incomplete, and suggested
using os.chmod(temp_path, 0o600) in the except AttributeError block.

After analyzing the code, we found that this fallback is ALREADY implemented in:
- _save method (lines 232-238)
- _save_with_todos method (lines 332-338)

This test suite verifies that the existing implementation works correctly.
"""

import os
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestWindowsPermissions:
    """Test that Windows properly falls back to os.chmod when os.fchmod is unavailable.

    Issue #212 suggests implementing os.chmod(temp_path, 0o600) as a fallback when
    os.fchmod is not available (Windows). This test verifies that this fallback
    mechanism is working correctly.
    """

    def test_save_without_fchmod_fallback(self):
        """Test _save_with_todos method properly handles AttributeError when os.fchmod is missing.

        This test simulates Windows behavior where os.fchmod raises AttributeError.
        It verifies that os.chmod is called as a fallback with 0o600 permissions.
        """
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_windows_permissions.json"

            # Track whether os.chmod was called
            with mock.patch('os.chmod') as mock_chmod:
                storage = Storage(str(storage_path))

                # Mock os.fchmod to raise AttributeError (simulating Windows behavior)
                with mock.patch('os.fchmod', side_effect=AttributeError("os.fchmod is not available")):
                    # Add a todo to trigger _save_with_todos
                    todo = Todo(title="Test Windows fallback", status="pending")
                    storage.add(todo)

                # Verify os.chmod was called as fallback
                assert mock_chmod.called, "os.chmod should be called when os.fchmod is unavailable"

                # Verify it was called with 0o600 (restrictive permissions)
                # Find the call with 0o600 mode
                chmod_calls_with_0600 = [
                    call for call in mock_chmod.call_args_list
                    if len(call[0]) >= 2 and call[0][1] == 0o600
                ]
                assert len(chmod_calls_with_0600) > 0, \
                    "os.chmod should be called with 0o600 permissions"

            # Verify the file was created
            assert storage_path.exists()

            # Verify file permissions are restrictive (on Unix systems)
            # On Windows: os.stat().st_mode behaves differently, but we verify the file exists
            if os.name != 'nt':
                file_stat = os.stat(storage_path)
                file_mode = file_stat.st_mode & 0o777
                assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

            # Verify the todo was actually saved
            todos = storage.list()
            assert len(todos) == 1
            assert todos[0].title == "Test Windows fallback"

    def test_save_without_fchmod_direct(self):
        """Test _save method directly with mocked os.fchmod.

        This test verifies that the _save method (used by _cleanup) also uses the
        chmod fallback correctly.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_save_direct.json"
            storage = Storage(str(storage_path))

            # Add initial todo
            todo1 = Todo(title="First todo", status="pending")
            storage.add(todo1)

            # Now mock os.fchmod and track os.chmod
            with mock.patch('os.fchmod', side_effect=AttributeError("os.fchmod is not available")), \
                 mock.patch('os.chmod') as mock_chmod:
                # This should trigger _save via _cleanup
                # Mark as dirty to trigger save
                storage._dirty = True
                storage._save()

                # Verify os.chmod was called
                assert mock_chmod.called, "os.chmod should be called as fallback in _save"

            # Verify file still exists and has correct content
            assert storage_path.exists()
            todos = storage.list()
            assert len(todos) == 1

    def test_fchmod_available_path(self):
        """Test that when os.fchmod is available, it's preferred over os.chmod.

        On Unix-like systems with os.fchmod available, it should be used instead
        of the os.chmod fallback.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_fchmod_preferred.json"

            # Mock both os.fchmod and os.chmod to track calls
            with mock.patch('os.chmod') as mock_chmod, \
                 mock.patch('os.fchmod') as mock_fchmod:
                storage = Storage(str(storage_path))
                todo = Todo(title="Test fchmod preference", status="pending")
                storage.add(todo)

                # Verify os.fchmod was called (preferred on Unix-like systems)
                assert mock_fchmod.called, "os.fchmod should be called when available"

                # os.chmod should NOT be called when os.fchmod is available
                # (except possibly for directory permissions, which we ignore)
                chmod_file_calls = [
                    call for call in mock_chmod.call_args_list
                    if len(call[0]) >= 2 and '.tmp' in str(call[0][0])
                ]
                assert len(chmod_file_calls) == 0, \
                    "os.chmod should not be called for temp files when os.fchmod is available"

    def test_windows_acl_basic_protection(self):
        """Test that Windows still gets basic protection via os.chmod fallback.

        This test simulates a Windows environment and verifies that even without
        os.fchmod, files are created with restrictive permissions via os.chmod.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_windows_protection.json"

            # Track if os.chmod was called as a fallback
            with mock.patch('os.chmod') as mock_chmod, \
                 mock.patch('os.fchmod', side_effect=AttributeError("os.fchmod is not available")):
                storage = Storage(str(storage_path))
                todo = Todo(title="Windows protection test", status="pending")
                storage.add(todo)

                # Verify os.chmod was called as fallback
                assert mock_chmod.called, "os.chmod should be called when os.fchmod is unavailable"

                # Verify it was called with 0o600 (restrictive permissions)
                chmod_calls_with_0600 = [
                    call for call in mock_chmod.call_args_list
                    if len(call[0]) >= 2 and call[0][1] == 0o600
                ]
                assert len(chmod_calls_with_0600) > 0, \
                    "os.chmod should be called with 0o600 permissions"

    def test_fallback_applied_before_write(self, tmp_path):
        """Test that chmod fallback is applied BEFORE data is written.

        This is a critical security test. The chmod must be applied before any
        data is written to prevent a race condition where the file could be
        accessed with default (loose) permissions.
        """
        storage_dir = tmp_path / "test_storage"
        storage_dir.mkdir()
        storage_path = storage_dir / "todos.json"

        # Track the order of operations
        operations = []

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

        # Find indices of critical operations
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

        # Verify all operations occurred
        assert fchmod_idx is not None, "fchmod should have been attempted"
        assert chmod_idx is not None, "chmod fallback should have been applied"
        assert write_idx is not None, "write should have been called"

        # THE CRITICAL CHECK: chmod must come BEFORE write
        # This ensures the file has restrictive permissions before any data is written
        assert chmod_idx < write_idx, \
            f"chmod must be applied before write to prevent race condition. " \
            f"Order: {[op[0] for op in operations]}"
