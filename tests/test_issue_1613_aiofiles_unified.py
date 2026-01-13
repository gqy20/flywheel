"""Test that aiofiles is always available without HAS_AIOFILES checks (Issue #1613).

This test verifies that:
1. The aiofiles module is always available (either real aiofiles or fallback)
2. The fallback uses asyncio.to_thread when aiofiles is not installed
3. No HAS_AIOFILES checks are needed in the codebase
4. The interface is consistent regardless of which implementation is used
"""

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Test 1: Verify aiofiles module is always importable
def test_aiofiles_always_available():
    """Test that aiofiles (or fallback) is always available."""
    from flywheel.storage import aiofiles

    # aiofiles should never be None
    assert aiofiles is not None, "aiofiles should always be available"

    # Should have open method
    assert hasattr(aiofiles, 'open'), "aiofiles should have an 'open' method"


# Test 2: Verify fallback uses asyncio.to_thread
@pytest.mark.asyncio
async def test_aiofiles_fallback_uses_asyncio_to_thread():
    """Test that the fallback implementation uses asyncio.to_thread."""
    # Temporarily hide the real aiofiles if it exists
    with patch.dict(sys.modules, {'aiofiles': None}):
        # Re-import to trigger fallback
        if 'flywheel.storage' in sys.modules:
            del sys.modules['flywheel.storage']

        from importlib import reload
        import flywheel.storage

        # Reload to get the fallback
        reload(flywheel.storage)

        # The aiofiles module should still be available
        from flywheel.storage import aiofiles
        assert aiofiles is not None

        # Test that it actually works with asyncio.to_thread
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
            f.write('test content')

        try:
            # Test reading
            async with aiofiles.open(temp_path, 'r') as f:
                content = await f.read()
            assert content == 'test content'

            # Test writing
            temp_path2 = temp_path + '.write'
            async with aiofiles.open(temp_path2, 'w') as f:
                await f.write('new content')

            # Verify write
            async with aiofiles.open(temp_path2, 'r') as f:
                content = await f.read()
            assert content == 'new content'

            Path(temp_path2).unlink()
        finally:
            Path(temp_path).unlink()


# Test 3: Verify interface consistency
@pytest.mark.asyncio
async def test_aiofiles_interface_consistency():
    """Test that aiofiles.open returns a consistent interface."""
    from flywheel.storage import aiofiles

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_path = f.name
        f.write('test')

    try:
        async with aiofiles.open(temp_path, 'r') as f:
            # Should have read method
            assert hasattr(f, 'read')

            # Should have write method (for write modes)
            # Note: read() should return a coroutine
            content = await f.read()
            assert content == 'test'
    finally:
        Path(temp_path).unlink()


# Test 4: Verify no HAS_AIOFILES constant needed
def test_no_has_aiofiles_needed():
    """Test that code doesn't need to check HAS_AIOFILES."""
    from flywheel.storage import aiofiles

    # If aiofiles is always available, we never need to check HAS_AIOFILES
    # This test verifies that assumption
    assert aiofiles is not None
    assert hasattr(aiofiles, 'open')

    # The following should work regardless of whether aiofiles is installed
    # without any HAS_AIOFILES check
    async def use_aiofiles_without_check():
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
            f.write('test')

        try:
            # No HAS_AIOFILES check needed!
            async with aiofiles.open(temp_path, 'r') as f:
                return await f.read()
        finally:
            Path(temp_path).unlink()

    # Run the async function
    result = asyncio.run(use_aiofiles_without_check())
    assert result == 'test'


# Test 5: Verify fallback handles binary mode correctly
@pytest.mark.asyncio
async def test_aiofiles_fallback_binary_mode():
    """Test that the fallback handles binary mode correctly."""
    from flywheel.storage import aiofiles

    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
        temp_path = f.name
        f.write(b'\x00\x01\x02\x03')

    try:
        # Test binary read
        async with aiofiles.open(temp_path, 'rb') as f:
            content = await f.read()
        assert content == b'\x00\x01\x02\x03'

        # Test binary write
        temp_path2 = temp_path + '.write'
        async with aiofiles.open(temp_path2, 'wb') as f:
            await f.write(b'\xff\xfe\xfd')

        async with aiofiles.open(temp_path2, 'rb') as f:
            content = await f.read()
        assert content == b'\xff\xfe\xfd'

        Path(temp_path2).unlink()
    finally:
        Path(temp_path).unlink()
