"""Tests for Issue #601 - FileNotFoundError should not log warning.

Issue: In `__init__`, catching `OSError` (including `FileNotFoundError`)
and only logging a warning. If the file doesn't exist, it should be
treated as a normal case (first run) without logging a warning.
"""

import os
import tempfile
import pytest
from unittest import mock
import logging

from flywheel.storage import FileStorage


class TestFileNotFoundErrorHandling:
    """Test that FileNotFoundError is handled silently (first run scenario)."""

    def test_file_not_found_no_warning(self, caplog):
        """FileNotFoundError should not log a warning (normal first run case)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a non-existent file path
            non_existent_path = os.path.join(tmpdir, "does_not_exist.json")

            # Creating FileStorage with non-existent file should NOT log warning
            with caplog.at_level(logging.WARNING):
                storage = FileStorage(non_existent_path)

            # Verify no warning was logged for FileNotFoundError
            for record in caplog.records:
                assert "Failed to load todos" not in record.message or \
                       "No such file or directory" not in record.message, \
                    "FileNotFoundError should not log a warning"

            # Verify storage is in valid initial state
            assert storage.list() == []
            assert storage._next_id == 1

    def test_other_oserror_logs_warning(self, caplog):
        """Other OSErrors (like PermissionError) should still log warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "test.json")

            # Mock _load to raise PermissionError (a type of OSError)
            with mock.patch.object(
                FileStorage, '_load', side_effect=PermissionError("Permission denied")
            ):
                with caplog.at_level(logging.WARNING):
                    storage = FileStorage(test_path)

            # Verify warning WAS logged for PermissionError
            assert any(
                "Failed to load todos" in record.message and
                "Permission denied" in record.message
                for record in caplog.records
            ), "Other OSErrors should still log warnings"

            # Verify storage is in valid initial state
            assert storage.list() == []
            assert storage._next_id == 1
