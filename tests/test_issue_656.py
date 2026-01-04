"""
Test for issue #656: Verify that atexit.register is only called when init_success is True

This test ensures that when FileStorage initialization fails critically,
the cleanup handler is NOT registered with atexit, preventing cleanup
attempts on partially initialized objects.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from flywheel.storage import FileStorage


class TestIssue656:
    """Test that atexit registration is controlled by init_success flag"""

    def test_atexit_not_registered_on_critical_failure(self, tmp_path):
        """
        Test that atexit.register is NOT called when initialization fails critically.

        This simulates a RuntimeError without backup (critical failure).
        The atexit.register should only be called when init_success is True.
        """
        # Create a test file with corrupted data that will cause a critical failure
        test_file = tmp_path / "test_critical_failure.json"

        # Write data that will fail validation (not a list)
        test_file.write_text('{"not": "a list"}')

        # Mock atexit.register to track if it gets called
        with patch('flywheel.storage.atexit.register') as mock_register:
            # This should raise RuntimeError due to format validation failure
            with pytest.raises(RuntimeError, match="Data format validation failed"):
                FileStorage(str(test_file))

            # Verify atexit.register was NOT called because init_success was False
            mock_register.assert_not_called()

    def test_atexit_registered_on_successful_init(self, tmp_path):
        """
        Test that atexit.register IS called when initialization succeeds.

        This is the positive case to ensure the normal flow still works.
        """
        test_file = tmp_path / "test_success.json"

        # Mock atexit.register to track if it gets called
        with patch('flywheel.storage.atexit.register') as mock_register:
            # Create FileStorage - file doesn't exist, which is a normal case
            storage = FileStorage(str(test_file))

            # Verify atexit.register WAS called because init_success was True
            mock_register.assert_called_once()
            # Verify it was called with the cleanup method
            assert mock_register.call_args[0][0] == storage._cleanup

    def test_atexit_registered_on_json_decode_error_with_recovery(self, tmp_path):
        """
        Test that atexit.register IS called when JSON decode error is handled gracefully.

        This tests the case where JSON parsing fails but we handle it gracefully
        by starting with empty state (init_success should be True).
        """
        test_file = tmp_path / "test_json_error.json"

        # Write invalid JSON
        test_file.write_text('{invalid json}')

        # Mock atexit.register to track if it gets called
        with patch('flywheel.storage.atexit.register') as mock_register:
            # This should NOT raise - it should handle the error gracefully
            storage = FileStorage(str(test_file))

            # Verify atexit.register WAS called because init_success was True
            # (we handled the error gracefully)
            mock_register.assert_called_once()
            assert mock_register.call_args[0][0] == storage._cleanup

    def test_atexit_registered_on_value_error_with_recovery(self, tmp_path):
        """
        Test that atexit.register IS called when ValueError is handled gracefully.

        This tests the case where data values are invalid but we handle it.
        """
        test_file = tmp_path / "test_value_error.json"

        # Write a list with invalid data that might cause ValueError
        # For example, a todo with an invalid priority value
        test_file.write_text(json.dumps([{"id": 1, "title": "test", "priority": "invalid"}]))

        # Mock atexit.register to track if it gets called
        with patch('flywheel.storage.atexit.register') as mock_register:
            # This should NOT raise - it should handle the error gracefully
            storage = FileStorage(str(test_file))

            # Verify atexit.register WAS called because init_success was True
            mock_register.assert_called_once()
            assert mock_register.call_args[0][0] == storage._cleanup

    def test_atexit_registered_on_file_not_found(self, tmp_path):
        """
        Test that atexit.register IS called when file doesn't exist.

        This is the normal first-run case.
        """
        test_file = tmp_path / "test_nonexistent.json"

        # Mock atexit.register to track if it gets called
        with patch('flywheel.storage.atexit.register') as mock_register:
            # Create FileStorage - file doesn't exist, which is normal
            storage = FileStorage(str(test_file))

            # Verify atexit.register WAS called because init_success was True
            mock_register.assert_called_once()
            assert mock_register.call_args[0][0] == storage._cleanup

    def test_atexit_registered_on_os_error_with_recovery(self, tmp_path):
        """
        Test that atexit.register IS called when OSError is handled gracefully.

        This simulates a permission error that we can recover from.
        """
        test_file = tmp_path / "test_os_error.json"

        # Mock _load_sync to raise PermissionError
        with patch('flywheel.storage.FileStorage._load_sync') as mock_load:
            mock_load.side_effect = PermissionError("Permission denied")

            # Mock atexit.register to track if it gets called
            with patch('flywheel.storage.atexit.register') as mock_register:
                # This should NOT raise - it should handle the error gracefully
                storage = FileStorage(str(test_file))

                # Verify atexit.register WAS called because init_success was True
                mock_register.assert_called_once()
                assert mock_register.call_args[0][0] == storage._cleanup
