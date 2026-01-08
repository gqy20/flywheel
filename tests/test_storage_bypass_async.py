"""Tests for FW_STORAGE_BYPASS_RETRY mode with async operations (Issue #1056)"""
import asyncio
import os
import pytest
from unittest.mock import patch, MagicMock

from flywheel.storage import storage_retry


class TestStorageBypassAsync:
    """Test that bypass mode handles both sync and async operations correctly"""

    def test_bypass_mode_with_sync_function(self):
        """Test bypass mode works correctly with synchronous functions"""
        # Define a sync function that would block
        def blocking_sync_operation():
            return "sync_result"

        with patch.dict(os.environ, {'FW_STORAGE_BYPASS_RETRY': '1'}):
            async def test():
                result = await storage_retry(
                    blocking_sync_operation,
                    operation_type="test_sync"
                )
                return result

            result = asyncio.run(test())
            assert result == "sync_result"

    def test_bypass_mode_with_async_function(self):
        """Test bypass mode works correctly with async functions (coroutines)

        This is the bug from Issue #1056: when an async function is passed,
        asyncio.to_thread would try to run it in a thread pool, which is
        incorrect. Async functions should be awaited directly.
        """
        # Define an async function
        async def async_operation():
            await asyncio.sleep(0.01)  # Simulate async I/O
            return "async_result"

        with patch.dict(os.environ, {'FW_STORAGE_BYPASS_RETRY': '1'}):
            async def test():
                result = await storage_retry(
                    async_operation,
                    operation_type="test_async"
                )
                return result

            # This should work correctly after the fix
            result = asyncio.run(test())
            assert result == "async_result"

    def test_bypass_mode_with_async_function_with_args(self):
        """Test bypass mode with async function that has arguments"""
        async def async_operation_with_args(value, multiplier=1):
            await asyncio.sleep(0.01)
            return value * multiplier

        with patch.dict(os.environ, {'FW_STORAGE_BYPASS_RETRY': '1'}):
            async def test():
                result = await storage_retry(
                    async_operation_with_args,
                    5,
                    multiplier=3,
                    operation_type="test_async_args"
                )
                return result

            result = asyncio.run(test())
            assert result == 15

    def test_bypass_mode_async_function_exception_handling(self):
        """Test that exceptions in async functions are properly propagated"""
        async def failing_async_operation():
            await asyncio.sleep(0.01)
            raise ValueError("Async operation failed")

        with patch.dict(os.environ, {'FW_STORAGE_BYPASS_RETRY': '1'}):
            async def test():
                with pytest.raises(ValueError, match="Async operation failed"):
                    await storage_retry(
                        failing_async_operation,
                        operation_type="test_async_fail"
                    )

            asyncio.run(test())

    def test_normal_mode_with_async_function(self):
        """Test that normal mode (non-bypass) also handles async functions correctly"""
        async def async_operation():
            await asyncio.sleep(0.01)
            return "normal_async_result"

        # Ensure bypass mode is not enabled
        env = os.environ.copy()
        env.pop('FW_STORAGE_BYPASS_RETRY', None)

        with patch.dict(os.environ, env, clear=True):
            async def test():
                result = await storage_retry(
                    async_operation,
                    operation_type="test_normal_async",
                    max_attempts=1
                )
                return result

            result = asyncio.run(test())
            assert result == "normal_async_result"
