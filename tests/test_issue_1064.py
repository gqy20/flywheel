"""Test for issue #1064: Fallback async implementation missing for aiofiles

This test verifies that _retry_io_operation is available regardless of whether
aiofiles is installed or not.
"""

import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import pytest

# Test that _retry_io_operation exists when aiofiles IS available
def test_retry_io_operation_exists_with_aiofiles():
    """
    Test that _retry_io_operation is defined even when aiofiles IS installed.

    This is the bug: the function is only defined inside 'if not HAS_AIOFILES'
    block, so it's missing when aiofiles is available.
    """

    # Create a mock aiofiles module
    mock_aiofiles = MagicMock()
    mock_aiofiles.open = MagicMock()

    # Mock aiofiles as available
    with patch.dict('sys.modules', {'aiofiles': mock_aiofiles}):
        # Remove storage module if already imported
        if 'flywheel.storage' in sys.modules:
            del sys.modules['flywheel.storage']

        try:
            # Import storage module with aiofiles "available"
            from flywheel.storage import _retry_io_operation

            # This should NOT raise AttributeError or ImportError
            # The function should be available regardless of aiofiles availability
            assert callable(_retry_io_operation), (
                "_retry_io_operation should be defined as a callable function "
                "even when aiofiles is installed. "
                "Fix: Move function definition outside the 'if not HAS_AIOFILES' block."
            )

            # Verify it's an async function
            import inspect
            assert inspect.iscoroutinefunction(_retry_io_operation), (
                "_retry_io_operation should be an async function"
            )

            # Verify the function signature includes expected parameters
            sig = inspect.signature(_retry_io_operation)
            expected_params = [
                'operation', 'max_attempts', 'initial_backoff', 'timeout',
                'path', 'operation_type', 'metrics'
            ]
            for param in expected_params:
                assert param in sig.parameters, (
                    f"_retry_io_operation should have parameter '{param}'"
                )

        except (AttributeError, ImportError) as e:
            pytest.fail(
                f"_retry_io_operation is not available when aiofiles is installed. "
                f"This is the bug described in issue #1064. "
                f"Error: {e}"
            )


def test_retry_io_operation_exists_without_aiofiles():
    """
    Test that _retry_io_operation is defined when aiofiles is NOT available.
    This should work (it's the current behavior).
    """

    # Remove aiofiles from sys.modules
    aiofiles_backup = sys.modules.get('aiofiles')
    if 'aiofiles' in sys.modules:
        del sys.modules['aiofiles']

    try:
        # Re-import storage module without aiofiles
        if 'flywheel.storage' in sys.modules:
            del sys.modules['flywheel.storage']

        from flywheel.storage import _retry_io_operation

        # This should work
        assert callable(_retry_io_operation)

    finally:
        # Restore aiofiles module
        if aiofiles_backup is not None:
            sys.modules['aiofiles'] = aiofiles_backup


@pytest.mark.asyncio
async def test_retry_io_operation_basic_functionality():
    """
    Test that _retry_io_operation actually works when called.
    This is a basic smoke test to ensure the function performs correctly.
    """
    # Remove aiofiles from sys.modules to test fallback behavior
    aiofiles_backup = sys.modules.get('aiofiles')
    if 'aiofiles' in sys.modules:
        del sys.modules['aiofiles']

    try:
        # Re-import storage module without aiofiles
        if 'flywheel.storage' in sys.modules:
            del sys.modules['flywheel.storage']

        from flywheel.storage import _retry_io_operation

        # Create a simple operation that will succeed
        async def simple_operation(x):
            return x * 2

        result = await _retry_io_operation(simple_operation, 5)
        assert result == 10, "Operation should execute successfully"

    finally:
        # Restore aiofiles module
        if aiofiles_backup is not None:
            sys.modules['aiofiles'] = aiofiles_backup


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
