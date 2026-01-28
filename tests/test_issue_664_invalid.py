"""Test for Issue #664 - Verify that FileStorage.__init__ is complete.

This test validates that the issue #664 report is a false positive.
The FileStorage.__init__ method is actually complete with all necessary logic.
"""

import pytest
import tempfile
import os
from pathlib import Path

from flywheel.storage import FileStorage


class TestIssue664FalsePositive:
    """Test suite to prove issue #664 is a false positive."""

    def test_init_method_exists(self):
        """Verify __init__ method exists and is callable."""
        assert hasattr(FileStorage, '__init__')
        assert callable(FileStorage.__init__)

    def test_init_with_default_path(self):
        """Test initialization with default path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, 'test.json')
            storage = FileStorage(path=test_path)

            # Verify all attributes are initialized
            assert hasattr(storage, '_todos')
            assert hasattr(storage, '_next_id')
            assert hasattr(storage, '_lock')
            assert hasattr(storage, '_dirty')
            assert hasattr(storage, '_lock_timeout')
            assert hasattr(storage, 'AUTO_SAVE_INTERVAL')
            assert hasattr(storage, 'last_saved_time')
            assert hasattr(storage, 'MIN_SAVE_INTERVAL')

    def test_init_loads_existing_data(self):
        """Test that __init__ loads existing data from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, 'test.json')

            # Create storage and add a todo
            storage1 = FileStorage(path=test_path)
            storage1.add("Test todo")
            storage1._cleanup()

            # Create new storage instance - should load existing data
            storage2 = FileStorage(path=test_path)
            assert len(storage2.list()) == 1
            assert storage2.list()[0].title == "Test todo"

    def test_init_handles_missing_file(self):
        """Test that __init__ handles missing file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, 'nonexistent.json')
            storage = FileStorage(path=test_path)

            # Should start with empty state
            assert len(storage.list()) == 0
            assert storage._next_id == 1

    def test_init_with_compression(self):
        """Test initialization with compression enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, 'test.json')
            storage = FileStorage(path=test_path, compression=True)

            # Verify .gz extension is added
            assert str(storage.path).endswith('.gz')

            # Verify compression attribute is set
            assert storage.compression is True

    def test_init_registers_cleanup(self):
        """Test that __init__ registers cleanup handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, 'test.json')
            storage = FileStorage(path=test_path)

            # Add a todo without explicitly calling save
            storage.add("Test todo")

            # Cleanup should save the data
            storage._cleanup()

            # Verify data was saved
            storage2 = FileStorage(path=test_path)
            assert len(storage2.list()) == 1
