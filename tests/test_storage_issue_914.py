"""Test that retry_transient_errors decorator is properly implemented (Issue #914).

This test verifies that the retry_transient_errors decorator is complete
and functional, addressing the claim that it was truncated at line 233.
"""

import errno

import pytest

from flywheel.storage import retry_transient_errors


class TestRetryDecoratorImplementation:
    """Test suite for retry_transient_errors decorator implementation."""

    def test_decorator_exists_and_is_callable(self):
        """Verify that the retry_transient_errors decorator exists and is callable."""
        assert callable(retry_transient_errors), "retry_transient_errors should be callable"

    def test_decorator_works_with_sync_functions(self):
        """Test that the decorator works with synchronous functions."""
        call_count = [0]

        @retry_transient_errors(max_attempts=3)
        def sync_function():
            call_count[0] += 1
            if call_count[0] < 2:
                # Fail on first attempt with transient error
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
            return "success"

        result = sync_function()
        assert result == "success"
        assert call_count[0] == 2, "Should have retried once"

    def test_decorator_works_with_async_functions(self):
        """Test that the decorator works with async functions."""
        import asyncio

        call_count = [0]

        @retry_transient_errors(max_attempts=3)
        async def async_function():
            call_count[0] += 1
            if call_count[0] < 2:
                # Fail on first attempt with transient error
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
            return "success"

        async def run_test():
            result = await async_function()
            assert result == "success"
            assert call_count[0] == 2, "Should have retried once"

        asyncio.run(run_test())

    def test_decorator_fails_on_permanent_errors(self):
        """Test that the decorator does not retry on permanent errors."""
        call_count = [0]

        @retry_transient_errors(max_attempts=3)
        def function_with_permanent_error():
            call_count[0] += 1
            raise IOError(errno.ENOSPC, "No space left on device")

        with pytest.raises(IOError):
            function_with_permanent_error()

        # Should only attempt once (no retry for permanent errors)
        assert call_count[0] == 1, "Should not retry on permanent errors"

    def test_decorator_respects_max_attempts(self):
        """Test that the decorator respects max_attempts parameter."""
        call_count = [0]

        @retry_transient_errors(max_attempts=2)
        def failing_function():
            call_count[0] += 1
            raise IOError(errno.EAGAIN, "Resource temporarily unavailable")

        with pytest.raises(IOError):
            failing_function()

        # Should attempt max_attempts times
        assert call_count[0] == 2, "Should respect max_attempts limit"

    def test_decorator_preserves_function_metadata(self):
        """Test that the decorator preserves function metadata."""
        @retry_transient_errors(max_attempts=3)
        def example_function():
            """Example function docstring."""
            pass

        assert example_function.__name__ == "example_function"
        assert example_function.__doc__ == "Example function docstring."
