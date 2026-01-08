"""Test I/O bypass mode feature (Issue #1048)."""
import os
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from flywheel.storage import _retry_io_operation, StorageTimeoutError


class TestBypassRetryMode:
    """Test bypass mode for I/O operations."""

    def test_bypass_retry_mode_enabled(self):
        """Test that bypass mode skips retry logic when env var is set."""
        with patch.dict(os.environ, {'FW_STORAGE_BYPASS_RETRY': '1'}):
            # Create a mock operation that will be called
            mock_operation = MagicMock(return_value='success')

            async def test_operation():
                result = await _retry_io_operation(
                    mock_operation,
                    path='/test/path',
                    operation_type='read',
                    max_attempts=3,  # Should be ignored in bypass mode
                    timeout=30.0  # Should be ignored in bypass mode
                )
                return result

            result = asyncio.run(test_operation())

            # In bypass mode, operation should be called exactly once
            assert mock_operation.call_count == 1
            assert result == 'success'

    def test_bypass_retry_mode_disabled(self):
        """Test that normal retry logic works when env var is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure the env var is not set
            os.environ.pop('FW_STORAGE_BYPASS_RETRY', None)

            # Create a mock operation that succeeds on first try
            mock_operation = MagicMock(return_value='success')

            async def test_operation():
                result = await _retry_io_operation(
                    mock_operation,
                    path='/test/path',
                    operation_type='read',
                    max_attempts=3
                )
                return result

            result = asyncio.run(test_operation())

            # Should be called once
            assert mock_operation.call_count == 1
            assert result == 'success'

    def test_bypass_retry_mode_with_transient_error(self):
        """Test that bypass mode does not retry on transient errors."""
        with patch.dict(os.environ, {'FW_STORAGE_BYPASS_RETRY': '1'}):
            import errno

            # Create a mock operation that fails with transient error
            mock_operation = MagicMock(side_effect=IOError(errno.EIO, "I/O error"))

            async def test_operation():
                try:
                    await _retry_io_operation(
                        mock_operation,
                        path='/test/path',
                        operation_type='read',
                        max_attempts=3  # Should be ignored in bypass mode
                    )
                    assert False, "Should have raised IOError"
                except IOError as e:
                    # Should fail immediately without retry
                    assert e.errno == errno.EIO
                    assert mock_operation.call_count == 1

            asyncio.run(test_operation())

    def test_bypass_retry_mode_with_timeout(self):
        """Test that bypass mode does not apply timeout."""
        with patch.dict(os.environ, {'FW_STORAGE_BYPASS_RETRY': '1'}):
            # Create a mock operation that succeeds
            mock_operation = MagicMock(return_value='success')

            async def test_operation():
                result = await _retry_io_operation(
                    mock_operation,
                    path='/test/path',
                    operation_type='read',
                    timeout=0.001  # Very short timeout, should be ignored
                )
                return result

            result = asyncio.run(test_operation())

            # Should succeed despite very short timeout
            assert mock_operation.call_count == 1
            assert result == 'success'

    def test_normal_mode_retries_on_transient_error(self):
        """Test that normal mode retries on transient errors."""
        with patch.dict(os.environ, {}, clear=True):
            import errno

            # Create a mock operation that fails twice then succeeds
            mock_operation = MagicMock(
                side_effect=[
                    IOError(errno.EIO, "I/O error 1"),
                    IOError(errno.EIO, "I/O error 2"),
                    'success'
                ]
            )

            async def test_operation():
                result = await _retry_io_operation(
                    mock_operation,
                    path='/test/path',
                    operation_type='read',
                    max_attempts=3,
                    initial_backoff=0.001  # Very short backoff for test
                )
                return result

            result = asyncio.run(test_operation())

            # Should have been called 3 times (2 failures + 1 success)
            assert mock_operation.call_count == 3
            assert result == 'success'
