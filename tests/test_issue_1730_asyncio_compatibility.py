"""Test for Issue #1730: Verify asyncio.to_thread compatibility.

This test verifies that _AiofilesPlaceholder handles asyncio.to_thread
correctly after removing the redundant local import.

The original issue claimed that `from asyncio import to_thread` at line 82
could fail on Python 3.8 and below. However:
1. The project requires Python >=3.13 (see pyproject.toml)
2. asyncio.to_thread was added in Python 3.9
3. asyncio is already imported at module level (line 4)

The fix removes the redundant local import and uses asyncio.to_thread
directly, which is cleaner and more consistent.
"""

import sys
import asyncio
import pytest
from pathlib import Path
import tempfile


class TestAsyncioToThreadCompatibility:
    """Test asyncio.to_thread compatibility in _AiofilesPlaceholder."""

    def test_asyncio_module_has_to_thread(self):
        """Verify that asyncio.to_thread is available in the current Python version."""
        # This should always pass since the project requires Python >=3.13
        assert hasattr(asyncio, 'to_thread'), \
            f"asyncio.to_thread not available in Python {sys.version}"

    def test_asyncio_to_thread_is_callable(self):
        """Verify that asyncio.to_thread is callable."""
        assert callable(asyncio.to_thread), \
            "asyncio.to_thread should be callable"

    @pytest.mark.asyncio
    async def test_can_use_asyncio_to_thread(self):
        """Verify that asyncio.to_thread actually works."""
        # Simple test: run a function in a thread pool
        def simple_func():
            return "result"

        result = await asyncio.to_thread(simple_func)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_aiofiles_placeholder_can_be_imported(self):
        """Verify that the storage module can be imported without ImportError."""
        # This test verifies that importing the storage module
        # doesn't raise an ImportError due to asyncio.to_thread
        try:
            from flywheel.storage import _AiofilesPlaceholder, aiofiles
            # If we get here, the import succeeded
            assert True
        except ImportError as e:
            if 'to_thread' in str(e):
                pytest.fail(f"ImportError related to to_thread: {e}")
            else:
                # Re-raise if it's a different import error
                raise

    @pytest.mark.asyncio
    async def test_aiofiles_placeholder_uses_module_level_asyncio(self):
        """Verify that _AiofilesPlaceholder uses module-level asyncio import."""
        import inspect
        from flywheel.storage import _AiofilesPlaceholder

        # Get the source code of the open method
        source = inspect.getsource(_AiofilesPlaceholder.open)

        # Verify that it uses asyncio.to_thread (not a local import)
        assert 'asyncio.to_thread' in source, \
            "_AiofilesPlaceholder.open should use asyncio.to_thread"

        # Verify that there's no local import of to_thread
        assert 'from asyncio import to_thread' not in source, \
            "_AiofilesPlaceholder.open should not have a local import of to_thread"

    @pytest.mark.asyncio
    async def test_aiofiles_fallback_works_without_aiofiles(self):
        """Test that the fallback implementation works when aiofiles is not available."""
        from flywheel.storage import HAS_AIOFILES

        if HAS_AIOFILES:
            pytest.skip("aiofiles is installed, cannot test fallback")

        # If aiofiles is not installed, the fallback should work
        from flywheel.storage import aiofiles

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
            f.write("test content")

        try:
            # Test that we can open and read the file
            async with await aiofiles.open(temp_path, 'r') as f:
                content = await f.read()

            assert content == "test content"
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_python_version_requirement(self):
        """Document that the project requires Python >=3.13."""
        # This test documents the minimum Python version
        # asyncio.to_thread was added in Python 3.9
        # The project requires Python >=3.13, so it's always available
        major, minor = sys.version_info[:2]
        assert major >= 3 and minor >= 13, \
            f"Project requires Python >=3.13, but running on {major}.{minor}"
