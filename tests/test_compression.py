"""Test compression support for FileStorage.

Tests for Issue #652: Add data compression storage support.
"""
import asyncio
import gzip
import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


@pytest.mark.asyncio
class TestCompressionSupport:
    """Test compression parameter in FileStorage."""

    async def test_compression_parameter_exists(self):
        """Test that FileStorage accepts compression parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "todos.json")
            # Should accept compression parameter
            storage = FileStorage(path, compression=True)
            assert hasattr(storage, 'compression')
            assert storage.compression is True

    async def test_compression_false_no_gzip_extension(self):
        """Test that compression=False does not add .gz extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "todos.json")
            storage = FileStorage(path, compression=False)
            # File should not have .gz extension when compression is disabled
            assert not str(storage.path).endswith('.gz')

    async def test_compression_true_adds_gzip_extension(self):
        """Test that compression=True adds .gz extension automatically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "todos.json")
            storage = FileStorage(path, compression=True)
            # File should have .gz extension when compression is enabled
            assert str(storage.path).endswith('.json.gz')

    async def test_save_with_compression_creates_gzip_file(self):
        """Test that saving with compression=True creates a gzip file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "todos.json")
            storage = FileStorage(path, compression=True)

            # Add a todo and save
            todo = Todo(id=1, title="Test todo", status="pending")
            await storage.add(todo)
            await storage._cleanup()

            # Check that file exists and is gzip compressed
            assert storage.path.exists()
            assert str(storage.path).endswith('.json.gz')

            # Verify it's a valid gzip file
            with gzip.open(storage.path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
                assert 'todos' in data
                assert len(data['todos']) == 1
                assert data['todos'][0]['title'] == "Test todo"

    async def test_save_without_compression_creates_regular_file(self):
        """Test that saving with compression=False creates a regular JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "todos.json")
            storage = FileStorage(path, compression=False)

            # Add a todo and save
            todo = Todo(id=1, title="Test todo", status="pending")
            await storage.add(todo)
            await storage._cleanup()

            # Check that file exists and is NOT gzip compressed
            assert storage.path.exists()
            assert not str(storage.path).endswith('.gz')

            # Verify it's a regular JSON file (not gzip)
            with open(storage.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert 'todos' in data
                assert len(data['todos']) == 1
                assert data['todos'][0]['title'] == "Test todo"

    async def test_load_with_compression(self):
        """Test loading data from a gzip-compressed file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "todos.json")
            storage = FileStorage(path, compression=True)

            # Create a gzip-compressed file manually
            data = {
                "todos": [{"id": 1, "title": "Test", "status": "pending"}],
                "next_id": 2,
                "metadata": {"checksum": "abc123"}
            }
            gz_path = Path(path + '.gz')
            with gzip.open(gz_path, 'wt', encoding='utf-8') as f:
                json.dump(data, f)

            # Load should read from gzip file
            new_storage = FileStorage(path, compression=True)
            await new_storage._load()
            assert len(new_storage._todos) == 1
            assert new_storage._todos[0].title == "Test"

    async def test_compression_defaults_to_false(self):
        """Test that compression defaults to False for backward compatibility."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "todos.json")
            # When compression parameter is not specified
            storage = FileStorage(path)
            assert storage.compression is False
            assert not str(storage.path).endswith('.gz')
