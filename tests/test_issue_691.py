"""Test for Issue #691 - _lock_range initialization.

This test verifies that the FileStorage class properly initializes
the _lock_range attribute in its __init__ method.

Issue: https://github.com/user/repo/issues/691
"""

import tempfile
import pytest
from pathlib import Path

from flywheel.storage import FileStorage


class TestIssue691:
    """Test that _lock_range attribute is properly initialized."""

    def test_lock_range_is_initialized(self):
        """Test that _lock_range attribute exists after initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(path=str(storage_path), compression=False)

            # Verify _lock_range attribute exists
            assert hasattr(storage, '_lock_range')

            # Verify it's initialized to 0
            assert storage._lock_range == 0

    def test_lock_range_is_initialized_with_compression(self):
        """Test that _lock_range attribute exists with compression enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            storage = FileStorage(path=str(storage_path), compression=True)

            # Verify _lock_range attribute exists
            assert hasattr(storage, '_lock_range')

            # Verify it's initialized to 0
            assert storage._lock_range == 0
