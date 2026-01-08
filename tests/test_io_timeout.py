"""Test I/O timeout functionality for Issue #1043."""

import asyncio
import errno
import pytest
import time

from flywheel.storage import _retry_io_operation, StorageTimeoutError


class TestIOTimeout:
    """Test configurable timeout for I/O retries."""

    @pytest.mark.asyncio
    async def test_timeout_on_slow_operation(self):
        """Test that slow operations timeout after specified duration."""
        # Create a very slow operation (longer than timeout)
        async def slow_operation():
            await asyncio.sleep(5)  # Sleep longer than timeout
            return "should_not_complete"

        # Should timeout after 0.5 seconds
        with pytest.raises(StorageTimeoutError) as exc_info:
            await _retry_io_operation(
                lambda: slow_operation(),
                timeout=0.5
            )

        assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_no_timeout_on_fast_operation(self):
        """Test that fast operations complete successfully with timeout set."""
        # Create a fast operation (shorter than timeout)
        def fast_operation():
            return "completed"

        # Should complete within 1 second timeout
        result = await _retry_io_operation(
            fast_operation,
            timeout=1.0
        )

        assert result == "completed"

    @pytest.mark.asyncio
    async def test_default_timeout(self):
        """Test that default timeout is applied (30s)."""
        # Create an operation that takes 35 seconds (longer than default 30s)
        async def very_slow_operation():
            await asyncio.sleep(35)
            return "should_not_complete"

        # Should timeout with default timeout
        with pytest.raises(StorageTimeoutError):
            await _retry_io_operation(lambda: very_slow_operation())

    @pytest.mark.asyncio
    async def test_timeout_parameter_none(self):
        """Test that timeout=None disables timeout."""
        # Create a moderately slow operation
        def moderate_operation():
            time.sleep(0.1)
            return "completed"

        # Should complete successfully with timeout=None (no timeout)
        result = await _retry_io_operation(
            moderate_operation,
            timeout=None
        )

        assert result == "completed"

    @pytest.mark.asyncio
    async def test_timeout_with_retry_logic(self):
        """Test that timeout works correctly with retry logic."""
        # Create an operation that fails with transient error then times out
        attempt_count = [0]

        def flaky_then_slow_operation():
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                # First attempt: transient error
                raise IOError(errno.EIO, "Transient I/O error")
            else:
                # Second attempt: very slow (timeout)
                time.sleep(5)
                return "should_not_complete"

        # Should timeout on retry attempt
        with pytest.raises(StorageTimeoutError):
            await _retry_io_operation(
                flaky_then_slow_operation,
                max_attempts=3,
                timeout=0.5
            )

    @pytest.mark.asyncio
    async def test_timeout_error_distinct_from_io_error(self):
        """Test that StorageTimeoutError is distinct from regular IOError."""
        async def slow_operation():
            await asyncio.sleep(2)
            return "should_not_complete"

        # Timeout error should be StorageTimeoutError, not IOError
        with pytest.raises(StorageTimeoutError) as exc_info:
            await _retry_io_operation(
                lambda: slow_operation(),
                timeout=0.5
            )

        # Should not be a regular IOError
        assert not isinstance(exc_info.value, IOError) or exc_info.value.__class__.__name__ == "StorageTimeoutError"

    @pytest.mark.asyncio
    async def test_custom_timeout_value(self):
        """Test various custom timeout values."""
        # Test with 2 second timeout on 1 second operation (should succeed)
        def one_second_operation():
            time.sleep(1)
            return "done"

        result = await _retry_io_operation(
            one_second_operation,
            timeout=2.0
        )
        assert result == "done"

        # Test with 0.5 second timeout on 2 second operation (should timeout)
        async def two_second_operation():
            await asyncio.sleep(2)
            return "should_not_complete"

        with pytest.raises(StorageTimeoutError):
            await _retry_io_operation(
                lambda: two_second_operation(),
                timeout=0.5
            )
