"""Test file descriptor handling in atomic writes."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_file_descriptor_not_closed_twice_on_replace_failure():
    """Test that file descriptor is not closed twice when Path.replace fails."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Mock Path.replace to raise an exception
        original_replace = Path.replace

        def mock_replace(self, target):
            # Simulate failure during atomic replace
            raise OSError("Simulated replace failure")

        with patch.object(Path, 'replace', mock_replace):
            storage = Storage(str(storage_path))

            # This should not raise an error about double-closing the file descriptor
            # If the fd is closed twice, we would get OSError: [Errno 9] Bad file descriptor
            with pytest.raises(OSError, match="Simulated replace failure"):
                storage.add(Todo(id=1, title="Test todo", status="pending"))


def test_file_descriptor_closed_on_write_failure():
    """Test that file descriptor is properly closed when os.write fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Mock os.write to raise an exception
        original_write = os.write

        def mock_write(fd, data):
            # Simulate failure during write
            raise OSError("Simulated write failure")

        with patch('os.write', mock_write):
            storage = Storage(str(storage_path))

            # This should raise an error but properly close the file descriptor
            with pytest.raises(OSError, match="Simulated write failure"):
                storage.add(Todo(id=1, title="Test todo", status="pending"))

            # Verify no file descriptors are leaked by checking storage is still functional
            # after the error (this would fail if fd was leaked)
            storage._todos = []
            storage._save()  # This should work without running out of file descriptors


def test_normal_save_does_not_leak_file_descriptors():
    """Test that normal save operations don't leak file descriptors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Perform multiple save operations
        for i in range(100):
            storage.add(Todo(id=i+1, title=f"Todo {i+1}", status="pending"))

        # If file descriptors were leaked, this would likely fail or show warnings
        # Verify storage still works
        todos = storage.list()
        assert len(todos) == 100
