"""Test for Issue #1750: File close exception handling."""

import asyncio
import tempfile
from unittest.mock import Mock, patch

import pytest

from flywheel.storage import Storage


@pytest.mark.asyncio
async def test_async_file_close_exception_is_propagated():
    """Test that exceptions during file close are not silently ignored (Issue #1750)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Get the async file wrapper
        async_file = storage.aiofiles.open(f"{tmpdir}/test.json", "w")

        # Mock the close method to raise an exception
        async def mock_close_with_error():
            raise IOError("Simulated close error")

        # Enter the context manager
        file_obj = await async_file.__aenter__()

        # Replace the close method with our mock
        original_close = file_obj.close

        async def close_with_error():
            raise IOError("Test close error")

        file_obj.close = close_with_error

        # Exiting should raise the exception, not swallow it
        with pytest.raises(IOError, match="Test close error"):
            await async_file.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_async_file_close_normal_operation():
    """Test that normal file close operation works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Get the async file wrapper
        async_file = storage.aiofiles.open(f"{tmpdir}/test.json", "w")

        # Use the file normally
        file_obj = await async_file.__aenter__()
        file_obj.write("test content")

        # Should not raise any exception
        await async_file.__aexit__(None, None, None)

        # File should be closed
        assert file_obj.closed
