"""Tests for @retry_io decorator (Issue #948)."""
import asyncio
import errno
from unittest.mock import patch

import pytest

from flywheel.storage import retry_io


class TestRetryIo:
    """Test suite for retry_io decorator."""

    def test_sync_function_success_on_first_attempt(self):
        """Test that sync function succeeds on first attempt."""
        @retry_io(max_retries=3, backoff_factor=0.5)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_async_function_success_on_first_attempt(self):
        """Test that async function succeeds on first attempt."""
        @retry_io(max_retries=3, backoff_factor=0.5)
        async def test_func():
            return "success"

        result = asyncio.run(test_func())
        assert result == "success"

    def test_sync_function_retries_on_eio(self):
        """Test that sync function retries on EIO (I/O error)."""
        call_count = 0

        @retry_io(max_retries=3, backoff_factor=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # First call fails with EIO
                error = OSError("I/O error")
                error.errno = errno.EIO
                raise error
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    def test_sync_function_retries_on_enospc(self):
        """Test that sync function retries on ENOSPC (no space)."""
        call_count = 0

        @retry_io(max_retries=3, backoff_factor=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # First call fails with ENOSPC
                error = OSError("No space left on device")
                error.errno = errno.ENOSPC
                raise error
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    def test_async_function_retries_on_eio(self):
        """Test that async function retries on EIO (I/O error)."""
        call_count = 0

        @retry_io(max_retries=3, backoff_factor=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # First call fails with EIO
                error = OSError("I/O error")
                error.errno = errno.EIO
                raise error
            return "success"

        result = asyncio.run(test_func())
        assert result == "success"
        assert call_count == 2

    def test_sync_function_fails_on_permanent_error(self):
        """Test that sync function fails immediately on ENOENT error."""
        @retry_io(max_retries=3, backoff_factor=0.01)
        def test_func():
            error = OSError("No such file or directory")
            error.errno = errno.ENOENT
            raise error

        with pytest.raises(OSError) as exc_info:
            test_func()
        assert exc_info.value.errno == errno.ENOENT

    def test_sync_function_exhausts_retries(self):
        """Test that sync function raises after exhausting retries."""
        @retry_io(max_retries=3, backoff_factor=0.01)
        def test_func():
            error = OSError("I/O error")
            error.errno = errno.EIO
            raise error

        with pytest.raises(OSError) as exc_info:
            test_func()
        assert exc_info.value.errno == errno.EIO

    def test_exponential_backoff(self):
        """Test that backoff increases exponentially."""
        call_count = 0
        sleep_times = []

        @retry_io(max_retries=4, backoff_factor=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                error = OSError("I/O error")
                error.errno = errno.EIO
                raise error
            return "success"

        original_sleep = __import__('time').sleep

        def mock_sleep(seconds):
            sleep_times.append(seconds)

        with patch('time.sleep', side_effect=mock_sleep):
            result = test_func()

        assert result == "success"
        assert call_count == 4
        # Check exponential backoff: 0.1, 0.2, 0.4
        assert len(sleep_times) == 3
        assert sleep_times[0] == 0.1
        assert sleep_times[1] == 0.2
        assert sleep_times[2] == 0.4

    def test_decorator_preserves_function_attributes(self):
        """Test that decorator preserves function name and docstring."""
        @retry_io(max_retries=3, backoff_factor=0.5)
        def my_sync_function():
            """This is a sync function."""
            pass

        @retry_io(max_retries=3, backoff_factor=0.5)
        async def my_async_function():
            """This is an async function."""
            pass

        assert my_sync_function.__name__ == "my_sync_function"
        assert my_sync_function.__doc__ == "This is a sync function."
        assert my_async_function.__name__ == "my_async_function"
        assert my_async_function.__doc__ == "This is an async function."

    def test_default_parameters(self):
        """Test that decorator works with default parameters."""
        @retry_io()
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_custom_max_retries(self):
        """Test custom max_retries parameter."""
        call_count = 0

        @retry_io(max_retries=5, backoff_factor=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                error = OSError("I/O error")
                error.errno = errno.EIO
                raise error
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 5

    def test_retry_on_eagain(self):
        """Test that it retries on EAGAIN (resource temporarily unavailable)."""
        call_count = 0

        @retry_io(max_retries=3, backoff_factor=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = OSError("Resource temporarily unavailable")
                error.errno = errno.EAGAIN
                raise error
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    def test_retry_on_ebusy(self):
        """Test that it retries on EBUSY (device busy)."""
        call_count = 0

        @retry_io(max_retries=3, backoff_factor=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = OSError("Device busy")
                error.errno = errno.EBUSY
                raise error
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2
