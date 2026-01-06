"""Tests for retry_transient_errors decorator (Issue #907)."""
import asyncio
import errno
import time
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import retry_transient_errors


class TestRetryTransientErrors:
    """Test suite for retry_transient_errors decorator."""

    def test_sync_function_success_on_first_attempt(self):
        """Test that sync function succeeds on first attempt."""
        @retry_transient_errors(max_attempts=3)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_async_function_success_on_first_attempt(self):
        """Test that async function succeeds on first attempt."""
        @retry_transient_errors(max_attempts=3)
        async def test_func():
            return "success"

        result = asyncio.run(test_func())
        assert result == "success"

    def test_sync_function_retries_on_transient_error(self):
        """Test that sync function retries on transient EAGAIN error."""
        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # First call fails with transient error
                error = IOError("Resource temporarily unavailable")
                error.errno = errno.EAGAIN
                raise error
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    def test_async_function_retries_on_transient_error(self):
        """Test that async function retries on transient EAGAIN error."""
        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # First call fails with transient error
                error = IOError("Resource temporarily unavailable")
                error.errno = errno.EAGAIN
                raise error
            return "success"

        result = asyncio.run(test_func())
        assert result == "success"
        assert call_count == 2

    def test_sync_function_fails_on_permanent_error(self):
        """Test that sync function fails immediately on ENOSPC error."""
        @retry_transient_errors(max_attempts=3, initial_backoff=0.01)
        def test_func():
            error = IOError("No space left on device")
            error.errno = errno.ENOSPC
            raise error

        with pytest.raises(IOError) as exc_info:
            test_func()
        assert exc_info.value.errno == errno.ENOSPC

    def test_async_function_fails_on_permanent_error(self):
        """Test that async function fails immediately on ENOSPC error."""
        @retry_transient_errors(max_attempts=3, initial_backoff=0.01)
        async def test_func():
            error = IOError("No space left on device")
            error.errno = errno.ENOSPC
            raise error

        with pytest.raises(IOError) as exc_info:
            asyncio.run(test_func())
        assert exc_info.value.errno == errno.ENOSPC

    def test_sync_function_exhausts_retries(self):
        """Test that sync function raises after exhausting retries."""
        @retry_transient_errors(max_attempts=3, initial_backoff=0.01)
        def test_func():
            error = IOError("Resource temporarily unavailable")
            error.errno = errno.EAGAIN
            raise error

        with pytest.raises(IOError) as exc_info:
            test_func()
        assert exc_info.value.errno == errno.EAGAIN

    def test_async_function_exhausts_retries(self):
        """Test that async function raises after exhausting retries."""
        @retry_transient_errors(max_attempts=3, initial_backoff=0.01)
        async def test_func():
            error = IOError("Resource temporarily unavailable")
            error.errno = errno.EAGAIN
            raise error

        with pytest.raises(IOError) as exc_info:
            asyncio.run(test_func())
        assert exc_info.value.errno == errno.EAGAIN

    def test_sync_function_uses_time_sleep(self):
        """Test that sync function uses time.sleep for backoff."""
        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = IOError("Resource temporarily unavailable")
                error.errno = errno.EAGAIN
                raise error
            return "success"

        with patch('time.sleep') as mock_sleep:
            result = test_func()
            assert result == "success"
            assert mock_sleep.called
            assert call_count == 2

    def test_async_function_uses_asyncio_sleep(self):
        """Test that async function uses asyncio.sleep for backoff."""
        call_count = 0

        @retry_transient_errors(max_attempts=3, initial_backoff=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = IOError("Resource temporarily unavailable")
                error.errno = errno.EAGAIN
                raise error
            return "success"

        with patch('asyncio.sleep') as mock_sleep:
            result = asyncio.run(test_func())
            assert result == "success"
            assert mock_sleep.called
            assert call_count == 2

    def test_decorator_preserves_function_attributes(self):
        """Test that decorator preserves function name and docstring."""
        @retry_transient_errors(max_attempts=3)
        def my_sync_function():
            """This is a sync function."""
            pass

        @retry_transient_errors(max_attempts=3)
        async def my_async_function():
            """This is an async function."""
            pass

        assert my_sync_function.__name__ == "my_sync_function"
        assert my_sync_function.__doc__ == "This is a sync function."
        assert my_async_function.__name__ == "my_async_function"
        assert my_async_function.__doc__ == "This is an async function."
