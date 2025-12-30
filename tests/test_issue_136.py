"""Tests for issue #136 - UnboundLocalError for backup_path in exception handlers."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import Storage


def test_backup_path_defined_before_try_block_json_decode_error():
    """Test that backup_path is defined before try block in JSONDecodeError handler.

    This test verifies the fix for issue #136 where backup_path was defined
    inside the try block, causing UnboundLocalError if an exception occurred
    before the assignment.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Create a file with invalid JSON
        test_file.write_text("{invalid json content")

        # Mock shutil.copy2 to raise an exception immediately
        # This simulates failure before backup_path assignment
        with patch('shutil.copy2') as mock_copy:
            mock_copy.side_effect = OSError("Mock copy failure")

            # This should raise RuntimeError, not UnboundLocalError
            # If backup_path is not defined before the try block,
            # the raise statement will fail with UnboundLocalError
            with pytest.raises(RuntimeError) as exc_info:
                Storage(path=str(test_file))

            # Verify the error message contains backup_path reference
            # If backup_path was undefined, this would fail with UnboundLocalError
            assert "Backup saved to" in str(exc_info.value)


def test_backup_path_defined_before_try_block_generic_exception():
    """Test that backup_path is defined before try block in generic Exception handler.

    This test verifies the fix for issue #136 where backup_path was defined
    inside the try block for the generic exception handler as well.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Create a file with valid but structurally invalid data (not dict or list)
        test_file.write_text('"just a string"')

        # Mock shutil.copy2 to raise an exception immediately
        with patch('shutil.copy2') as mock_copy:
            mock_copy.side_effect = OSError("Mock copy failure")

            # This should raise RuntimeError, not UnboundLocalError
            with pytest.raises(RuntimeError) as exc_info:
                Storage(path=str(test_file))

            # Verify the error message contains backup_path reference
            assert "Backup saved to" in str(exc_info.value)


def test_backup_path_variable_scope_in_exception_handlers():
    """Test that backup_path is accessible in all exception handler code paths.

    This is a comprehensive test that ensures backup_path is properly scoped
    in both exception handlers (JSONDecodeError and generic Exception).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Test JSONDecodeError path
        test_file.write_text("{bad")

        # Even when backup creation fails, the raise statement should work
        with patch('shutil.copy2') as mock_copy:
            mock_copy.side_effect = Exception("Backup failed")

            with pytest.raises(RuntimeError) as exc_info:
                Storage(path=str(test_file))

            # The error message should reference backup_path
            error_msg = str(exc_info.value)
            assert "Backup saved to" in error_msg
            assert ".backup" in error_msg
