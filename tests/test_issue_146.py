"""Tests for Issue #146 - Duplicate backup logic and variable definition error."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage


def test_backup_path_variable_scope():
    """Test that backup_path is properly scoped and accessible in exception handlers.

    This test verifies that when a JSON decode error occurs during loading,
    the backup mechanism works correctly without UnboundLocalError.
    """
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a malformed JSON file
        test_file = Path(tmpdir) / "todos.json"
        test_file.write_text("{invalid json content")

        # Try to create Storage with malformed JSON
        # This should trigger the JSONDecodeError exception handler
        # and create a backup file
        with pytest.raises(RuntimeError) as exc_info:
            Storage(path=str(test_file))

        # Verify the error message mentions backup
        assert "Backup" in str(exc_info.value)

        # Verify backup file was created
        backup_file = Path(str(test_file) + ".backup")
        assert backup_file.exists(), "Backup file should be created when JSON is invalid"

        # Verify backup contains the same malformed content
        assert backup_file.read_text() == test_file.read_text()


def test_backup_path_in_general_exception():
    """Test that backup_path is properly scoped in general exception handler.

    This test verifies that when a general exception occurs during loading
    (e.g., permission error, file system error), the backup mechanism works.
    """
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a JSON file with invalid structure that will cause RuntimeError
        test_file = Path(tmpdir) / "todos.json"
        test_file.write_text(json.dumps("invalid_type_should_be_dict_or_list"))

        # Try to create Storage with invalid structure
        # This should trigger the general Exception handler
        with pytest.raises(RuntimeError) as exc_info:
            Storage(path=str(test_file))

        # Verify the error message mentions backup
        assert "Backup" in str(exc_info.value)

        # Verify backup file was created
        backup_file = Path(str(test_file) + ".backup")
        assert backup_file.exists(), "Backup file should be created on general exception"


def test_no_unboundlocalerror_in_exception_handlers():
    """Ensure backup_path variable is accessible in both exception handlers.

    This is a regression test for Issue #146 to prevent UnboundLocalError.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test JSON decode error path
        test_file = Path(tmpdir) / "test1.json"
        test_file.write_text('{"invalid": }')

        with pytest.raises(RuntimeError):
            Storage(path=str(test_file))

        backup = Path(str(test_file) + ".backup")
        assert backup.exists()

        # Test general exception path
        test_file2 = Path(tmpdir) / "test2.json"
        test_file2.write_text(json.dumps(123))  # Invalid type (not dict or list)

        with pytest.raises(RuntimeError):
            Storage(path=str(test_file2))

        backup2 = Path(str(test_file2) + ".backup")
        assert backup2.exists()
