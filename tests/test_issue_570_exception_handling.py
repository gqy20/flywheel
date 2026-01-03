"""Tests for issue #570: Specific exception handling in __init__"""

import json
import pytest
from pathlib import Path
from flywheel import Storage


class TestSpecificExceptionHandling:
    """Test that __init__ catches specific exceptions, not broad Exception."""

    def test_init_catches_json_decode_error(self, tmp_path):
        """Test that JSON decode errors are handled gracefully."""
        storage_path = tmp_path / "test.json"

        # Write invalid JSON
        storage_path.write_text("{invalid json}")

        # Should not raise, should log warning and start with empty state
        storage = Storage(storage_path)
        assert storage.list() == []

    def test_init_catches_io_error(self, tmp_path):
        """Test that IO errors are handled gracefully."""
        storage_path = tmp_path / "test.json"

        # Create a directory instead of a file (will cause IOError on read)
        storage_path.mkdir()

        # Should not raise, should log warning and start with empty state
        storage = Storage(storage_path)
        assert storage.list() == []

    def test_init_catches_permission_error(self, tmp_path):
        """Test that permission errors are handled gracefully."""
        storage_path = tmp_path / "test.json"

        # Write a file with no read permissions
        storage_path.write_text('{"todos": [], "next_id": 1}')
        storage_path.chmod(0o000)

        try:
            # Should not raise, should log warning and start with empty state
            storage = Storage(storage_path)
            assert storage.list() == []
        finally:
            # Restore permissions for cleanup
            storage_path.chmod(0o644)

    def test_init_does_not_catch_system_exit(self, tmp_path):
        """Test that SystemExit is NOT caught (should propagate)."""
        from unittest.mock import patch

        storage_path = tmp_path / "test.json"

        # Mock _load to raise SystemExit
        with patch.object(Storage, '_load', side_effect=SystemExit(1)):
            # SystemExit should propagate and not be caught
            with pytest.raises(SystemExit):
                Storage(storage_path)

    def test_init_does_not_catch_keyboard_interrupt(self, tmp_path):
        """Test that KeyboardInterrupt is NOT caught (should propagate)."""
        from unittest.mock import patch

        storage_path = tmp_path / "test.json"

        # Mock _load to raise KeyboardInterrupt
        with patch.object(Storage, '_load', side_effect=KeyboardInterrupt()):
            # KeyboardInterrupt should propagate and not be caught
            with pytest.raises(KeyboardInterrupt):
                Storage(storage_path)
