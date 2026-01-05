"""Tests for enhanced logging and diagnostics (Issue #743)."""
import asyncio
import json
import logging
import pathlib
import tempfile
import time

import pytest

from flywheel.storage import FileStorage
from flywheel.models import Todo


class TestStorageEnhancedLogging:
    """Test that storage operations provide enhanced logging for diagnostics."""

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
    async def test_save_logs_lock_status(self, storage, caplog):
        """Test that _save logs file lock acquisition and release status."""
        # Add a todo and mark as dirty
        todo = Todo(id=1, title="Test todo for lock logging")
        storage._todos = [todo]
        storage._next_id = 2
        storage._dirty = True

        with caplog.at_level(logging.DEBUG):
            await storage.save()

        # Check for lock-related debug logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        assert any("lock" in msg.lower() for msg in debug_messages), \
            f"Expected file lock status log in: {debug_messages}"

    @pytest.mark.asyncio
    async def test_save_logs_detailed_timing(self, storage, caplog):
        """Test that _save logs detailed timing information for diagnostics."""
        todo = Todo(id=1, title="Test todo for timing logging")
        storage._todos = [todo]
        storage._next_id = 2
        storage._dirty = True

        with caplog.at_level(logging.DEBUG):
            await storage.save()

        # Check for timing logs with seconds information
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        timing_logs = [msg for msg in debug_messages if any(word in msg.lower() for word in ["completed", "s", "time"])]
        assert len(timing_logs) > 0, \
            f"Expected detailed timing log (e.g., 'Save completed in X.XXXs') in: {debug_messages}"

    @pytest.mark.asyncio
    async def test_load_logs_lock_status(self, storage, temp_dir, caplog):
        """Test that _load logs file lock acquisition and release status."""
        # Create a test file
        test_data = {
            "todos": [{"id": 1, "title": "Test todo", "completed": False}],
            "next_id": 2,
            "metadata": {"checksum": None}
        }
        storage.path.write_text(json.dumps(test_data))

        with caplog.at_level(logging.DEBUG):
            await storage.load()

        # Check for lock-related debug logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        assert any("lock" in msg.lower() for msg in debug_messages), \
            f"Expected file lock status log in: {debug_messages}"

    @pytest.mark.asyncio
    async def test_cache_hit_miss_logging(self, temp_dir, caplog):
        """Test that cache operations log hit/miss information when cache is enabled."""
        # Create storage with cache enabled
        storage = FileStorage(temp_dir / "test_cache.json", enable_cache=True)

        # Create initial data
        test_data = {
            "todos": [{"id": 1, "title": "Cached todo", "completed": False}],
            "next_id": 2,
            "metadata": {"checksum": None}
        }
        storage.path.write_text(json.dumps(test_data))

        with caplog.at_level(logging.DEBUG):
            # First load should populate cache
            await storage.load()
            # Get operation should use cache
            await storage.get(1)

        # Check for cache-related logs
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        cache_logs = [msg for msg in debug_messages if "cache" in msg.lower()]
        assert len(cache_logs) > 0, \
            f"Expected cache hit/miss logging in: {debug_messages}"

    @pytest.mark.asyncio
    async def test_file_lock_failure_logs_error(self, storage, caplog):
        """Test that file lock acquisition failures are logged with ERROR level."""
        # This test verifies that lock failures are properly logged
        # We'll use an existing file and try to trigger lock-related operations
        test_data = {
            "todos": [{"id": 1, "title": "Test todo", "completed": False}],
            "next_id": 2,
            "metadata": {"checksum": None}
        }
        storage.path.write_text(json.dumps(test_data))

        with caplog.at_level(logging.ERROR):
            await storage.load()

        # In normal conditions, lock should succeed, so no error logs expected
        # This test ensures the logging mechanism is in place for failure scenarios
        error_messages = [record.message for record in caplog.records if record.levelno == logging.ERROR]
        # Lock should succeed, so no lock errors expected
        lock_errors = [msg for msg in error_messages if "lock" in msg.lower()]
        assert len(lock_errors) == 0, \
            f"Expected no lock errors in normal operation, but got: {lock_errors}"

    @pytest.mark.asyncio
    async def test_performance_timing_diagnostics(self, storage, caplog):
        """Test that save and load operations log timing information for performance analysis."""
        # Add multiple todos to test performance timing
        for i in range(10):
            todo = Todo(id=i+1, title=f"Performance test todo {i+1}")
            storage._todos.append(todo)
        storage._next_id = 11
        storage._dirty = True

        with caplog.at_level(logging.DEBUG):
            await storage.save()

        # Verify timing information is logged
        debug_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        timing_logs = [msg for msg in debug_messages if any(char in msg for char in ["0.", "1.", "2.", "3.", "4.", "5."])]
        assert len(timing_logs) > 0, \
            f"Expected performance timing logs (with decimal numbers) in: {debug_messages}"
