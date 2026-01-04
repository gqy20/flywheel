"""
Test for Issue #590: RuntimeError without backup info should be re-raised

This test verifies that when a RuntimeError is raised during initialization
and the error message does NOT contain backup information, the exception is
properly re-raised to inform the caller of the failure.

The issue description claimed that the error was being ignored, but the code
actually re-raises the exception correctly. This test documents and verifies
the correct behavior.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, mock_open
from pathlib import Path

from flywheel.storage import TodoList


class TestIssue590RuntimeErrorWithoutBackup:
    """Test RuntimeError handling when no backup is created"""

    def test_runtime_error_without_backup_re_raises(self):
        """
        Test that RuntimeError without backup info is re-raised.

        When _load() raises a RuntimeError that doesn't contain backup
        information (e.g., format validation errors that don't trigger backup),
        the exception should be re-raised to inform the caller of the failure.

        This verifies the fix for issue #590: the code should NOT ignore
        the error but should propagate it to the caller.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")

            # Create a file with invalid schema that triggers format validation
            # This will raise RuntimeError WITHOUT backup info
            with open(storage_path, 'w') as f:
                # Invalid schema: 'metadata' is not a dict
                f.write('{"todos": [], "metadata": "invalid"}')

            # Attempting to create TodoList should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                TodoList(storage_path)

            # Verify the exception was raised
            assert exc_info is not None
            error_msg = str(exc_info.value)

            # This should be a format validation error without backup
            assert "Invalid schema" in error_msg or "metadata" in error_msg
            # Should NOT contain backup info
            assert "Backup saved to" not in error_msg
            assert "Backup created at" not in error_msg

    def test_runtime_error_with_backup_succeeds(self):
        """
        Test that RuntimeError WITH backup info allows initialization to succeed.

        When _load() raises a RuntimeError that contains backup information,
        the initialization should handle it gracefully and set init_success=True.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")

            # Create a file with invalid JSON that triggers backup creation
            with open(storage_path, 'w') as f:
                f.write('{"invalid json content')

            # This should succeed because backup is created
            todo_list = TodoList(storage_path)

            # Should be initialized with empty state
            assert todo_list._todos == []
            assert todo_list._next_id == 1
            assert not todo_list._dirty

    def test_init_success_not_set_when_runtime_error_re_raised(self):
        """
        Test that init_success remains False when RuntimeError is re-raised.

        This verifies that atexit cleanup is NOT registered when initialization
        fails critically with a RuntimeError without backup.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")

            # Create a file with invalid schema
            with open(storage_path, 'w') as f:
                f.write('{"todos": [], "metadata": "invalid"}')

            # Track atexit registrations
            import atexit
            initial_handlers = len(atexit._exithandlers)

            # Attempting to create TodoList should raise
            with pytest.raises(RuntimeError):
                TodoList(storage_path)

            # Number of handlers should not have increased
            # (no atexit registration happened for the failed object)
            final_handlers = len(atexit._exithandlers)
            # Note: There might be other handlers, so we check that it didn't increase
            # due to our failed initialization attempt
            assert final_handlers == initial_handlers

    def test_critical_error_prevents_object_use(self):
        """
        Test that when RuntimeError is re-raised, object cannot be used.

        This verifies that callers are properly notified of the failure
        and cannot accidentally use a partially initialized object.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "test.json")

            # Create invalid schema file
            with open(storage_path, 'w') as f:
                f.write('{"next_id": "not an int"}')

            # Should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                todo_list = TodoList(storage_path)

                # If we somehow get here (which we shouldn't), verify object is NOT usable
                assert False, "Should have raised RuntimeError"

            # Verify the error message is informative
            error_msg = str(exc_info.value)
            assert len(error_msg) > 0
