"""Test for issue #1036: Fallback async file operations text mode support."""

import asyncio
import pytest
from pathlib import Path

# Test with aiofiles fallback (when aiofiles is not available)
@pytest.mark.asyncio
async def test_fallback_text_mode_read(tmp_path):
    """Test that fallback async file operations handle text mode correctly."""
    # Skip if aiofiles is available
    try:
        import aiofiles
        if not hasattr(aiofiles, '__module__') or aiofiles.__module__ != 'flywheel.storage':
            pytest.skip("aiofiles is available, testing fallback only")
    except ImportError:
        pass

    from flywheel.storage import aiofiles

    # Create a test file with text content
    test_file = tmp_path / "test.txt"
    test_content = "Hello, World! 你好世界"
    test_file.write_text(test_content, encoding='utf-8')

    # Test reading in text mode - should return str, not bytes
    async with aiofiles.open(str(test_file), mode='r') as f:
        content = await f.read()
        # The issue: read() returns bytes but file is opened in text mode
        # This should be fixed to return str when in text mode
        assert isinstance(content, str), f"Expected str, got {type(content)}"
        assert content == test_content


@pytest.mark.asyncio
async def test_fallback_binary_mode_read(tmp_path):
    """Test that fallback async file operations handle binary mode correctly."""
    # Skip if aiofiles is available
    try:
        import aiofiles
        if not hasattr(aiofiles, '__module__') or aiofiles.__module__ != 'flywheel.storage':
            pytest.skip("aiofiles is available, testing fallback only")
    except ImportError:
        pass

    from flywheel.storage import aiofiles

    # Create a test file with binary content
    test_file = tmp_path / "test.bin"
    test_content = b"Binary data \x00\x01\x02"
    test_file.write_bytes(test_content)

    # Test reading in binary mode - should return bytes
    async with aiofiles.open(str(test_file), mode='rb') as f:
        content = await f.read()
        assert isinstance(content, bytes), f"Expected bytes, got {type(content)}"
        assert content == test_content


@pytest.mark.asyncio
async def test_fallback_text_mode_write(tmp_path):
    """Test that fallback async file operations can write in text mode."""
    # Skip if aiofiles is available
    try:
        import aiofiles
        if not hasattr(aiofiles, '__module__') or aiofiles.__module__ != 'flywheel.storage':
            pytest.skip("aiofiles is available, testing fallback only")
    except ImportError:
        pass

    from flywheel.storage import aiofiles

    # Create a test file with text content
    test_file = tmp_path / "test_write.txt"
    test_content = "Hello, World! 你好世界"

    # Test writing in text mode
    async with aiofiles.open(str(test_file), mode='w') as f:
        await f.write(test_content)

    # Verify the content
    assert test_file.read_text(encoding='utf-8') == test_content
