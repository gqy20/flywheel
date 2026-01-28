"""Tests for storage performance logging with byte counts (Issue #758)."""
import asyncio
import json
import logging
import pathlib
import tempfile

import pytest

from flywheel.storage import FileStorage
from flywheel.models import Todo


class TestStoragePerformanceLogging:
    """Test that storage operations log performance metrics including byte counts."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield pathlib.Path(tmpdir)

    @pytest.mark.asyncio
    async def test_async_load_logs_byte_count(self, temp_dir, caplog):
        """Test that async _load logs the number of bytes read."""
        # Create a test file with known content
        test_data = {
            "todos": [
                {"id": 1, "title": "Test todo 1", "completed": False},
                {"id": 2, "title": "Test todo 2", "completed": True},
            ],
            "next_id": 3,
            "metadata": {"checksum": None}
        }
        test_file = temp_dir / "test_load.json"
        test_content = json.dumps(test_data)
        test_file.write_text(test_content)

        storage = FileStorage(test_file)

        with caplog.at_level(logging.DEBUG):
            await storage.load()

        # Check for byte count in logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        byte_logs = [msg for msg in debug_messages if "byte" in msg.lower()]

        assert len(byte_logs) > 0, \
            f"Expected byte count log in: {debug_messages}"

        # Verify the log mentions bytes read
        assert any("read" in msg.lower() or "load" in msg.lower() for msg in byte_logs), \
            f"Expected log to mention read/load with bytes: {byte_logs}"

    @pytest.mark.asyncio
    async def test_async_save_logs_byte_count(self, temp_dir, caplog):
        """Test that async _save logs the number of bytes written."""
        storage = FileStorage(temp_dir / "test_save.json")

        # Add some todos
        todo1 = Todo(id=1, title="Test todo 1", completed=False)
        todo2 = Todo(id=2, title="Test todo 2", completed=True)
        storage._todos = [todo1, todo2]
        storage._next_id = 3
        storage._dirty = True

        with caplog.at_level(logging.DEBUG):
            await storage.save()

        # Check for byte count in logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        byte_logs = [msg for msg in debug_messages if "byte" in msg.lower()]

        assert len(byte_logs) > 0, \
            f"Expected byte count log in: {debug_messages}"

        # Verify the log mentions bytes written
        assert any("wrote" in msg.lower() or "write" in msg.lower() or "save" in msg.lower()
                   for msg in byte_logs), \
            f"Expected log to mention write/save with bytes: {byte_logs}"

    def test_sync_load_logs_byte_count(self, temp_dir, caplog):
        """Test that sync _load_sync logs the number of bytes read."""
        # Create a test file with known content
        test_data = {
            "todos": [
                {"id": 1, "title": "Test todo 1", "completed": False},
                {"id": 2, "title": "Test todo 2", "completed": True},
            ],
            "next_id": 3,
            "metadata": {"checksum": None}
        }
        test_file = temp_dir / "test_load_sync.json"
        test_content = json.dumps(test_data)
        test_file.write_text(test_content)

        with caplog.at_level(logging.DEBUG):
            # Creating storage calls _load_sync in __init__
            storage = FileStorage(test_file)

        # Check for byte count in logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        byte_logs = [msg for msg in debug_messages if "byte" in msg.lower()]

        assert len(byte_logs) > 0, \
            f"Expected byte count log in: {debug_messages}"

        # Verify the log mentions bytes read
        assert any("read" in msg.lower() or "load" in msg.lower() for msg in byte_logs), \
            f"Expected log to mention read/load with bytes: {byte_logs}"

    def test_sync_save_logs_byte_count(self, temp_dir, caplog):
        """Test that sync _save_with_todos_sync logs the number of bytes written."""
        storage = FileStorage(temp_dir / "test_save_sync.json")

        # Add some todos
        todo1 = Todo(id=1, title="Test todo 1", completed=False)
        todo2 = Todo(id=2, title="Test todo 2", completed=True)
        storage._todos = [todo1, todo2]
        storage._next_id = 3
        storage._dirty = True

        with caplog.at_level(logging.DEBUG):
            # add() is a sync method that calls _save_with_todos_sync
            todo = Todo(id=3, title="New todo", completed=False)
            storage.add(todo)

        # Check for byte count in logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        byte_logs = [msg for msg in debug_messages if "byte" in msg.lower()]

        assert len(byte_logs) > 0, \
            f"Expected byte count log in: {debug_messages}"

        # Verify the log mentions bytes written
        assert any("wrote" in msg.lower() or "write" in msg.lower() or "save" in msg.lower()
                   for msg in byte_logs), \
            f"Expected log to mention write/save with bytes: {byte_logs}"

    @pytest.mark.asyncio
    async def test_performance_log_includes_time_and_bytes(self, temp_dir, caplog):
        """Test that performance logs include both timing and byte information."""
        # Create a test file
        test_data = {
            "todos": [{"id": 1, "title": "Test todo", "completed": False}],
            "next_id": 2,
            "metadata": {"checksum": None}
        }
        test_file = temp_dir / "test_perf.json"
        test_content = json.dumps(test_data)
        test_file.write_text(test_content)

        storage = FileStorage(test_file)

        with caplog.at_level(logging.DEBUG):
            await storage.load()

        # Check for logs that include both timing and byte info
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]

        # Should have timing info (contains 's' for seconds)
        timing_logs = [msg for msg in debug_messages if 's' in msg and ('completed' in msg.lower() or 'load' in msg.lower())]
        assert len(timing_logs) > 0, f"Expected timing log in: {debug_messages}"

        # Should have byte info
        byte_logs = [msg for msg in debug_messages if 'byte' in msg.lower()]
        assert len(byte_logs) > 0, f"Expected byte count log in: {debug_messages}"
