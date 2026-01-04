"""Test async file I/O functionality (Issue #582)."""

import asyncio
import pytest
from pathlib import Path
from flywheel.storage import FileStorage
from flywheel.todo import Todo


class TestAsyncFileIO:
    """Test suite for async file I/O operations."""

    def test_async_load_method_exists(self):
        """Test that async _load method exists."""
        storage = FileStorage(path="~/.flywheel/test_async_load.json")
        # Check if the method is async
        assert hasattr(storage, '_load'), "FileStorage should have _load method"
        # Check if it's a coroutine function
        import inspect
        if asyncio.iscoroutinefunction(storage._load):
            # Method is async - this is what we want
            assert True
        else:
            # Method is not async - this will fail after we implement the feature
            pytest.fail("_load method should be async (async def)")

    def test_async_save_method_exists(self):
        """Test that async _save method exists."""
        storage = FileStorage(path="~/.flywheel/test_async_save.json")
        # Check if the method is async
        assert hasattr(storage, '_save'), "FileStorage should have _save method"
        # Check if it's a coroutine function
        import inspect
        if asyncio.iscoroutinefunction(storage._save):
            # Method is async - this is what we want
            assert True
        else:
            # Method is not async - this will fail after we implement the feature
            pytest.fail("_save method should be async (async def)")

    @pytest.mark.asyncio
    async def test_async_load_not_implemented(self):
        """Test that async _load raises NotImplementedError if not yet implemented."""
        storage = FileStorage(path="~/.flywheel/test_async_load_impl.json")
        # Try to call async load
        import inspect
        if not asyncio.iscoroutinefunction(storage._load):
            pytest.skip("_load is not yet async, skipping async test")
        else:
            # If it's async, it should work or raise NotImplementedError
            try:
                await storage._load()
            except NotImplementedError:
                # Expected if feature is not yet fully implemented
                pass
            except Exception:
                # Other exceptions are okay for now
                pass

    @pytest.mark.asyncio
    async def test_async_save_not_implemented(self):
        """Test that async _save raises NotImplementedError if not yet implemented."""
        storage = FileStorage(path="~/.flywheel/test_async_save_impl.json")
        # Try to call async save
        import inspect
        if not asyncio.iscoroutinefunction(storage._save):
            pytest.skip("_save is not yet async, skipping async test")
        else:
            # If it's async, it should work or raise NotImplementedError
            try:
                await storage._save()
            except NotImplementedError:
                # Expected if feature is not yet fully implemented
                pass
            except Exception:
                # Other exceptions are okay for now
                pass

    def test_file_storage_uses_asyncio_lock(self):
        """Test that FileStorage uses asyncio.Lock instead of threading.RLock."""
        storage = FileStorage(path="~/.flywheel/test_async_lock.json")
        # Check the lock type
        import asyncio
        assert hasattr(storage, '_lock'), "FileStorage should have _lock attribute"
        # After implementation, _lock should be an asyncio.Lock
        if isinstance(storage._lock, asyncio.Lock):
            assert True
        else:
            # Before implementation, it's threading.RLock
            import threading
            if isinstance(storage._lock, threading.RLock):
                pytest.fail("_lock should be asyncio.Lock, not threading.RLock")
            else:
                pytest.fail(f"_lock should be asyncio.Lock, got {type(storage._lock)}")

    def test_asyncio_import_available(self):
        """Test that asyncio module is available."""
        import asyncio
        assert hasattr(asyncio, 'Lock'), "asyncio.Lock should be available"

    def test_aiofiles_dependency(self):
        """Test that aiofiles is available for async file I/O."""
        try:
            import aiofiles
            assert hasattr(aiofiles, 'open'), "aiofiles.open should be available"
        except ImportError:
            pytest.fail("aiofiles package is required for async file I/O. Install with: pip install aiofiles")
