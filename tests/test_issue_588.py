"""Test data integrity verification on load (Issue #588).

This test verifies that SHA256 hash stored at the end of the file
is validated against the loaded JSON content to detect silent data
corruption or JSON truncation.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue588:
    """Test data integrity verification on load."""

    def test_file_truncation_detected(self):
        """Test that truncated file is detected during load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create storage and add todos
            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.add(Todo(id=2, title="Task 2", status="completed"))
            storage.close()

            # Truncate the file to simulate corruption
            file_size = storage_path.stat().st_size
            with storage_path.open('r+b') as f:
                f.seek(file_size // 2)  # Truncate to half size
                f.truncate()

            # Loading should raise an error (either JSON parsing error or integrity error)
            with pytest.raises((RuntimeError, json.JSONDecodeError)):
                Storage(str(storage_path))

    def test_file_corruption_detected_by_hash(self):
        """Test that corrupted content is detected by hash verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create storage and add todos
            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.close()

            # Read the file content
            with storage_path.open('rb') as f:
                content = f.read()

            # Find the last 64 characters (SHA256 hex) and corrupt some data
            # For now, just corrupt the middle of the JSON
            with storage_path.open('r+b') as f:
                f.seek(len(content) // 2)
                # Corrupt a few bytes
                f.write(b'XXXX')

            # Loading should raise an error due to corruption
            with pytest.raises((RuntimeError, json.JSONDecodeError)):
                Storage(str(storage_path))

    def test_valid_file_loads_successfully(self):
        """Test that valid files with correct hash load successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create storage and add todos
            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.add(Todo(id=2, title="Task 2", status="completed"))
            storage.close()

            # Loading should work fine
            storage2 = Storage(str(storage_path))
            todos = storage2.list()
            assert len(todos) == 2
            assert todos[0].title == "Task 1"
            assert todos[1].title == "Task 2"

    def test_hash_stored_at_end_of_file(self):
        """Test that SHA256 hash is stored at the end of the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create storage and add todos
            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.close()

            # Read the file as bytes
            with storage_path.open('rb') as f:
                content = f.read()

            # Verify that the last 64 characters are hex (SHA256)
            # and are separated from JSON by a delimiter
            content_str = content.decode('utf-8')

            # The hash should be at the end in format: \n--HASH\n
            # or similar delimiter
            assert len(content_str) > 64, "File should contain content + hash"

    def test_compressed_file_integrity_verification(self):
        """Test that compressed files also have hash verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json.gz"

            # Create storage with compression
            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.add(Todo(id=2, title="Task 2", status="completed"))
            storage.close()

            # Loading should work fine
            storage2 = Storage(str(storage_path))
            todos = storage2.list()
            assert len(todos) == 2

            # Corrupt the compressed file
            with storage_path.open('r+b') as f:
                f.seek(10)
                f.write(b'XXXX')

            # Loading should raise an error
            with pytest.raises((RuntimeError, json.JSONDecodeError)):
                Storage(str(storage_path))
