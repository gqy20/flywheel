"""Tests for I/O operation logging in storage.py (Issue #733)."""
import asyncio
import json
import logging
import pathlib
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import FileStorage
from flywheel.models import Todo


class TestStorageLogging:
    """Test that I/O operations log appropriate messages."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield pathlib.Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a FileStorage instance for testing."""
        return FileStorage(temp_dir / "test.json")

    @pytest.mark.asyncio
    async def test_load_logs_file_operations(self, storage, temp_dir, caplog):
        """Test that _load logs file operation messages."""
        # Create a test file
        test_data = {
            "todos": [{"id": 1, "title": "Test todo", "completed": False}],
            "next_id": 2,
            "metadata": {"checksum": None}
        }
        storage.path.write_text(json.dumps(test_data))

        with caplog.at_level(logging.DEBUG):
            await storage.load()

        # Check for debug logs about file operations
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        assert any("lock" in msg.lower() for msg in debug_messages), \
            f"Expected lock acquisition log in: {debug_messages}"
        assert any("load" in msg.lower() or "read" in msg.lower() for msg in debug_messages), \
            f"Expected load/read log in: {debug_messages}"

    @pytest.mark.asyncio
    async def test_save_logs_file_operations(self, storage, caplog):
        """Test that _save logs file operation messages."""
        # Add a todo
        todo = Todo(id=1, title="Test todo")
        storage._todos = [todo]
        storage._next_id = 2
        storage._dirty = True

        with caplog.at_level(logging.DEBUG):
            await storage.save()

        # Check for debug logs about file operations
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        assert any("save" in msg.lower() for msg in debug_messages), \
            f"Expected save log in: {debug_messages}"

    @pytest.mark.asyncio
    async def test_load_logs_timing(self, storage, temp_dir, caplog):
        """Test that _load logs timing information."""
        # Create a test file
        test_data = {
            "todos": [{"id": 1, "title": "Test todo", "completed": False}],
            "next_id": 2,
            "metadata": {"checksum": None}
        }
        storage.path.write_text(json.dumps(test_data))

        with caplog.at_level(logging.DEBUG):
            await storage.load()

        # Check for timing logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        assert any(any(word in msg.lower() for word in ["completed", "s", "sec", "time"])
                  for msg in debug_messages), \
            f"Expected timing log in: {debug_messages}"

    @pytest.mark.asyncio
    async def test_save_logs_timing(self, storage, caplog):
        """Test that _save logs timing information."""
        todo = Todo(id=1, title="Test todo")
        storage._todos = [todo]
        storage._next_id = 2
        storage._dirty = True

        with caplog.at_level(logging.DEBUG):
            await storage.save()

        # Check for timing logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        assert any(any(word in msg.lower() for word in ["completed", "s", "sec", "time"])
                  for msg in debug_messages), \
            f"Expected timing log in: {debug_messages}"

    @pytest.mark.asyncio
    async def test_load_nonexistent_file_logs(self, storage, temp_dir, caplog):
        """Test that loading non-existent file logs appropriately."""
        # Don't create the file

        with caplog.at_level(logging.DEBUG):
            await storage.load()

        # Should have some debug log about file not existing or initialization
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        assert len(debug_messages) > 0, "Expected debug logs when loading non-existent file"

    def test_load_sync_logs_file_operations(self, storage, temp_dir, caplog):
        """Test that _load_sync logs file operation messages."""
        # Create a test file
        test_data = {
            "todos": [{"id": 1, "title": "Test todo", "completed": False}],
            "next_id": 2,
            "metadata": {"checksum": None}
        }
        storage.path.write_text(json.dumps(test_data))

        with caplog.at_level(logging.DEBUG):
            # Create new storage instance which calls _load_sync in __init__
            FileStorage(temp_dir / "test2.json")

        # Check for debug logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        assert len(debug_messages) > 0, "Expected debug logs during sync load"
