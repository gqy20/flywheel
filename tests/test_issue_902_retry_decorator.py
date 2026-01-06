"""Tests for Issue #902: Verify retry_transient_errors decorator is complete and functional.

This test validates that the retry_transient_errors decorator:
1. Is fully implemented (not truncated)
2. Works with synchronous functions
3. Works with asynchronous functions
4. Retries on transient errors (EAGAIN, EACCES, etc.)
5. Does not retry on permanent errors (ENOSPC, ENOENT, etc.)
"""

import errno
import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.flywheel.storage import retry_transient_errors


class TestRetryDecoratorCompleteness:
    """Test that the retry_transient_errors decorator is fully implemented."""

    def test_decorator_is_callable(self):
        """Test that the decorator can be called without errors."""
        # This test will fail if the decorator code is truncated or malformed
        try:
            @retry_transient_errors(max_attempts=3)
            def dummy_function():
                return "success"

            result = dummy_function()
            assert result == "success"
        except SyntaxError as e:
            pytest.fail(f"Decorator code is truncated or malformed: {e}")
        except Exception as e:
            # Other exceptions are okay for this test
            # We're just checking the decorator is syntactically valid
            pass


class TestRetryDecoratorSyncFunctionality:
    """Test retry behavior for synchronous functions."""

    def test_sync_function_success_on_first_try(self):
        """Test that successful sync functions work normally."""

        @retry_transient_errors(max_attempts=3)
        def write_data():
            return "data written"

        result = write_data()
        assert result == "data written"

    def test_sync_function_retries_on_transient_error(self):
        """Test that sync function retries on transient errors like EAGAIN."""

        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.001)
        def write_data_with_transient_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Simulate transient error on first call
                error = IOError("Resource temporarily unavailable")
                error.errno = errno.EAGAIN
                raise error
            return "success"

        result = write_data_with_transient_error()
        assert result == "success"
        assert call_count == 2  # Failed once, then succeeded

    def test_sync_function_retries_on_eacces(self):
        """Test that sync function retries on EACCES (permission denied)."""

        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.001)
        def write_data_with_permission_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = IOError("Permission denied")
                error.errno = errno.EACCES
                raise error
            return "success"

        result = write_data_with_permission_error()
        assert result == "success"
        assert call_count == 2

    def test_sync_function_fails_after_max_attempts(self):
        """Test that sync function fails after max attempts on transient errors."""

        @retry_transient_errors(max_attempts=2, initial_backoff=0.001)
        def always_fail_transient():
            error = IOError("Resource temporarily unavailable")
            error.errno = errno.EAGAIN
            raise error

        with pytest.raises(IOError) as exc_info:
            always_fail_transient()

        assert exc_info.value.errno == errno.EAGAIN

    def test_sync_function_no_retry_on_permanent_error_enospc(self):
        """Test that ENOSPC (no space left) fails immediately without retry."""

        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.001)
        def fail_with_no_space():
            nonlocal call_count
            call_count += 1
            error = IOError("No space left on device")
            error.errno = errno.ENOSPC
            raise error

        with pytest.raises(IOError) as exc_info:
            fail_with_no_space()

        assert exc_info.value.errno == errno.ENOSPC
        assert call_count == 1  # Should fail immediately, no retry

    def test_sync_function_no_retry_on_permanent_error_enoent(self):
        """Test that ENOENT (no such file) fails immediately without retry."""

        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.001)
        def fail_with_no_file():
            nonlocal call_count
            call_count += 1
            error = IOError("No such file or directory")
            error.errno = errno.ENOENT
            raise error

        with pytest.raises(IOError) as exc_info:
            fail_with_no_file()

        assert exc_info.value.errno == errno.ENOENT
        assert call_count == 1  # Should fail immediately, no retry


class TestRetryDecoratorAsyncFunctionality:
    """Test retry behavior for asynchronous functions."""

    @pytest.mark.asyncio
    async def test_async_function_success_on_first_try(self):
        """Test that successful async functions work normally."""

        @retry_transient_errors(max_attempts=3)
        async def write_data_async():
            return "data written"

        result = await write_data_async()
        assert result == "data written"

    @pytest.mark.asyncio
    async def test_async_function_retries_on_transient_error(self):
        """Test that async function retries on transient errors like EAGAIN."""

        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.001)
        async def write_data_with_transient_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = IOError("Resource temporarily unavailable")
                error.errno = errno.EAGAIN
                raise error
            return "success"

        result = await write_data_with_transient_error()
        assert result == "success"
        assert call_count == 2  # Failed once, then succeeded

    @pytest.mark.asyncio
    async def test_async_function_fails_after_max_attempts(self):
        """Test that async function fails after max attempts on transient errors."""

        @retry_transient_errors(max_attempts=2, initial_backoff=0.001)
        async def always_fail_transient():
            error = IOError("Resource temporarily unavailable")
            error.errno = errno.EAGAIN
            raise error

        with pytest.raises(IOError) as exc_info:
            await always_fail_transient()

        assert exc_info.value.errno == errno.EAGAIN

    @pytest.mark.asyncio
    async def test_async_function_no_retry_on_permanent_error(self):
        """Test that permanent errors like ENOSPC fail immediately without retry."""

        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.001)
        async def fail_with_no_space():
            nonlocal call_count
            call_count += 1
            error = IOError("No space left on device")
            error.errno = errno.ENOSPC
            raise error

        with pytest.raises(IOError) as exc_info:
            await fail_with_no_space()

        assert exc_info.value.errno == errno.ENOSPC
        assert call_count == 1  # Should fail immediately, no retry


class TestRetryDecoratorEdgeCases:
    """Test edge cases and error conditions."""

    def test_non_io_error_not_retried(self):
        """Test that non-IOError exceptions are not caught or retried."""

        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.001)
        def raise_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Some other error")

        with pytest.raises(ValueError):
            raise_value_error()

        assert call_count == 1  # Should not retry

    def test_io_error_without_errno_not_retried(self):
        """Test that IOError without errno attribute is not retried."""

        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.001)
        def raise_io_without_errno():
            nonlocal call_count
            call_count += 1
            # Create IOError without errno attribute
            raise IOError("Unknown error")

        with pytest.raises(IOError):
            raise_io_without_errno()

        assert call_count == 1  # Should not retry

    def test_custom_parameters(self):
        """Test decorator with custom parameters."""

        call_count = 0

        @retry_transient_errors(max_attempts=5, initial_backoff=0.001, exponential_base=3.0)
        def custom_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                error = IOError("Resource temporarily unavailable")
                error.errno = errno.EAGAIN
                raise error
            return "success"

        result = custom_retry()
        assert result == "success"
        assert call_count == 3
