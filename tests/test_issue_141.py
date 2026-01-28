"""Tests for Issue #141 - RuntimeError for invalid format should not trigger backup."""

import json
import tempfile
from pathlib import Path
import pytest

from flywheel.storage import Storage


def test_invalid_format_should_not_create_backup():
    """Test that invalid data format (non-dict/list) raises RuntimeError without backup.

    Issue #141: When _load detects invalid data format (not dict/list), it raises
    RuntimeError, but this exception is caught by the generic except Exception block
    at line 111, which triggers the backup mechanism. This is not desired behavior
    for format errors - backups should only be created for JSON decode errors.

    The test ensures that:
    1. RuntimeError is raised for invalid format
    2. No backup file is created
    3. The error message is clear about the format issue
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Create a file with invalid format (string instead of dict/list)
        with test_file.open('w') as f:
            json.dump("this is a string, not dict or list", f)

        backup_file = Path(str(test_file) + ".backup")

        # Attempt to create Storage with invalid format file
        # This should raise RuntimeError without creating a backup
        with pytest.raises(RuntimeError) as exc_info:
            Storage(path=str(test_file))

        # Verify the error message mentions format issue
        assert "Invalid data format" in str(exc_info.value)
        assert "expected dict or list" in str(exc_info.value)

        # Verify NO backup file was created
        assert not backup_file.exists(), "Backup should not be created for format errors"


def test_json_decode_error_should_create_backup():
    """Test that JSON decode errors still create backups as expected.

    This test ensures that while invalid format errors don't create backups,
    actual JSON decode errors still do create backups (preserving existing behavior).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # Create a file with invalid JSON (not properly formatted)
        with test_file.open('w') as f:
            f.write("{ invalid json }")

        backup_file = Path(str(test_file) + ".backup")

        # Attempt to create Storage with invalid JSON file
        # This should raise RuntimeError AND create a backup
        with pytest.raises(RuntimeError) as exc_info:
            Storage(path=str(test_file))

        # Verify the error message mentions JSON issue
        assert "Invalid JSON" in str(exc_info.value)

        # Verify backup file WAS created (for JSON decode errors)
        assert backup_file.exists(), "Backup should be created for JSON decode errors"
