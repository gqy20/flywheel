"""Test for issue #39 - Unsafe file descriptor handling."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_handles_partial_writes():
    """Test that _save handles partial writes correctly."""
    # Create a storage instance with a temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(id=1, title="Test todo", status="pending")
        storage._todos = [todo]

        # Mock os.write to simulate partial writes
        original_write = os.write
        call_count = [0]

        def mock_write(fd, data):
            call_count[0] += 1
            # Simulate partial write on first call (write only 10 bytes)
            if call_count[0] == 1:
                return original_write(fd, data[:10])
            # Write the rest on subsequent calls
            return original_write(fd, data)

        with patch('os.write', side_effect=mock_write):
            # This should handle partial writes gracefully
            storage._save()

        # Verify the file was written correctly
        assert storage_path.exists()
        content = storage_path.read_text()
        loaded_data = json.loads(content)
        assert len(loaded_data) == 1
        assert loaded_data[0]["id"] == 1
        assert loaded_data[0]["title"] == "Test todo"


def test_save_with_todos_handles_partial_writes():
    """Test that _save_with_todos handles partial writes correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create multiple todos to ensure we have enough data
        todos = [
            Todo(id=i, title=f"Todo {i}", status="pending")
            for i in range(1, 11)
        ]

        # Mock os.write to simulate partial writes
        original_write = os.write
        call_count = [0]

        def mock_write(fd, data):
            call_count[0] += 1
            # Simulate partial write (write only 50 bytes at a time)
            chunk_size = 50
            if len(data) > chunk_size and call_count[0] == 1:
                return original_write(fd, data[:chunk_size])
            return original_write(fd, data)

        with patch('os.write', side_effect=mock_write):
            # This should handle partial writes gracefully
            storage._save_with_todos(todos)

        # Verify the file was written correctly
        assert storage_path.exists()
        content = storage_path.read_text()
        loaded_data = json.loads(content)
        assert len(loaded_data) == 10
        assert loaded_data[0]["id"] == 1
        assert loaded_data[9]["id"] == 10


def test_save_large_data():
    """Test saving a large amount of todo data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create a large number of todos to test handling of large data
        todos = [
            Todo(id=i, title=f"This is a longer title for todo number {i}", status="pending")
            for i in range(1, 101)
        ]

        # This should work without issues
        storage._save_with_todos(todos)

        # Verify the file was written correctly
        assert storage_path.exists()
        content = storage_path.read_text()
        loaded_data = json.loads(content)
        assert len(loaded_data) == 100
        assert loaded_data[0]["id"] == 1
        assert loaded_data[99]["id"] == 100
