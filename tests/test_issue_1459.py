"""Tests for Issue #1459 - Verify context manager methods are complete."""
import pytest
import asyncio
from flywheel.storage import FileStorage, MemoryStorage


class TestSyncContextManager:
    """Test synchronous context manager protocol."""

    def test_context_manager_has_exit_method(self):
        """Verify __exit__ method exists and is callable."""
        storage = MemoryStorage()
        assert hasattr(storage._lock, '__exit__')
        assert callable(storage._lock.__exit__)

    def test_sync_context_manager_works(self):
        """Verify sync context manager works correctly."""
        storage = MemoryStorage()
        with storage._lock:
            # Lock should be held within context
            assert storage._lock._lock.locked()
        # Lock should be released after context
        assert not storage._lock._lock.locked()


class TestAsyncContextManager:
    """Test asynchronous context manager protocol."""

    @pytest.mark.asyncio
    async def test_async_context_manager_has_aenter_method(self):
        """Verify __aenter__ method exists and is callable."""
        storage = MemoryStorage()
        assert hasattr(storage._lock, '__aenter__')
        assert callable(storage._lock.__aenter__)

    @pytest.mark.asyncio
    async def test_async_context_manager_has_aexit_method(self):
        """Verify __aexit__ method exists and is callable."""
        storage = MemoryStorage()
        assert hasattr(storage._lock, '__aexit__')
        assert callable(storage._lock.__aexit__)

    @pytest.mark.asyncio
    async def test_async_context_manager_works(self):
        """Verify async context manager works correctly."""
        storage = MemoryStorage()
        async with storage._lock:
            # Lock should be held within context
            assert storage._lock._lock.locked()
        # Lock should be released after context
        assert not storage._lock._lock.locked()

    @pytest.mark.asyncio
    async def test_async_and_sync_mutex(self):
        """Verify async and sync contexts are mutually exclusive."""
        storage = MemoryStorage()
        sync_acquired = False
        async_acquired = False

        async def async_task():
            nonlocal async_acquired
            async with storage._lock:
                async_acquired = True
                await asyncio.sleep(0.1)
                async_acquired = False

        # Start async task
        task = asyncio.create_task(async_task())

        # Wait a bit for async to acquire lock
        await asyncio.sleep(0.05)

        # Try to acquire sync lock - should wait
        with storage._lock:
            sync_acquired = True
            assert not async_acquired  # Async should have released
            sync_acquired = False

        await task


class TestContextManagerSignatures:
    """Verify context manager methods have correct signatures."""

    def test_exit_signature(self):
        """Verify __exit__ has correct parameters."""
        import inspect
        storage = MemoryStorage()
        sig = inspect.signature(storage._lock.__exit__)
        params = list(sig.parameters.keys())
        assert params == ['exc_type', 'exc_val', 'exc_tb']

    @pytest.mark.asyncio
    async def test_aexit_signature(self):
        """Verify __aexit__ has correct parameters."""
        import inspect
        storage = MemoryStorage()
        sig = inspect.signature(storage._lock.__aexit__)
        params = list(sig.parameters.keys())
        assert params == ['exc_type', 'exc_val', 'exc_tb']
