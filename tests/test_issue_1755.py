"""
Test for issue #1755: Original exception should not be suppressed in __aexit__

This test ensures that when an exception occurs in the context body AND
file close also fails, the original exception from the context body is
properly re-raised rather than being silently swallowed.
"""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest


class OriginalException(Exception):
    """Exception raised in the context body."""
    pass


class CloseException(Exception):
    """Exception raised during file close."""
    pass


@pytest.mark.asyncio
async def test_simple_async_file_exit_preserves_original_exception():
    """
    Test that _SimpleAsyncFile.__aexit__ re-raises the original exception
    even when file close also fails.

    This test creates a scenario where:
    1. An exception (OriginalException) is raised in the context body
    2. File close also raises an exception (CloseException)

    The expected behavior is that the OriginalException should be re-raised,
    not silently swallowed or replaced by CloseException.
    """
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.json"

        # Create the file so it can be opened
        test_file.write_text("{}")

        # Import and get _SimpleAsyncFile from _AiofilesPlaceholder
        from flywheel.storage import _AiofilesPlaceholder

        # Get the _SimpleAsyncFile class
        async_file_context = _AiofilesPlaceholder.open(test_file, 'r')

        # Create a file wrapper that will raise on close
        original_file = None
        close_mock = MagicMock(side_effect=CloseException("Close failed"))

        async def test_context_body():
            nonlocal original_file

            # Create the async file context
            async with async_file_context as f:
                original_file = f

                # Replace the close method with a mock that raises CloseException
                with patch.object(f, 'close', close_mock):
                    # Raise an exception in the context body
                    raise OriginalException("Original exception in context")

        # The test should raise OriginalException, not CloseException
        with pytest.raises(OriginalException) as exc_info:
            await test_context_body()

        # Verify it's the original exception
        assert str(exc_info.value) == "Original exception in context"
        assert type(exc_info.value) == OriginalException


@pytest.mark.asyncio
async def test_simple_async_file_exit_close_exception_without_context_exception():
    """
    Test that _SimpleAsyncFile.__aexit__ raises close exception
    when there is no exception from the context body.

    This is the control test to verify normal close exception handling.
    """
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.json"

        # Create the file so it can be opened
        test_file.write_text("{}")

        # Import and get _SimpleAsyncFile from _AiofilesPlaceholder
        from flywheel.storage import _AiofilesPlaceholder

        # Get the _SimpleAsyncFile class
        async_file_context = _AiofilesPlaceholder.open(test_file, 'r')

        # Create a file wrapper that will raise on close
        close_mock = MagicMock(side_effect=CloseException("Close failed"))

        async def test_context_body():
            # Create the async file context
            async with async_file_context as f:
                # Replace the close method with a mock that raises CloseException
                with patch.object(f, 'close', close_mock):
                    # No exception in context body
                    pass

        # When no context exception, close exception should be raised
        with pytest.raises(CloseException) as exc_info:
            await test_context_body()

        # Verify it's the close exception
        assert str(exc_info.value) == "Close failed"
        assert type(exc_info.value) == CloseException


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
