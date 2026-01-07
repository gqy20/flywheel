"""Tests for retry decorator with logger parameter (Issue #937)."""

import errno
import logging
import time
from unittest.mock import Mock, patch

import pytest

from flywheel.storage import retry_transient_errors


class TestRetryDecoratorWithLogger:
    """Test that retry decorator accepts and uses a custom logger."""

    def test_retry_with_custom_logger_sync(self):
        """Test that synchronous retry decorator accepts a custom logger parameter."""
        # Create a custom logger
        custom_logger = Mock(spec=logging.Logger)
        custom_logger.debug = Mock()
        custom_logger.warning = Mock()

        # Track the number of attempts
        attempts = 0

        @retry_transient_errors(max_attempts=3, logger=custom_logger)
        def failing_operation():
            nonlocal attempts
            attempts += 1
            # Raise a transient error on first two attempts
            if attempts < 3:
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
            return "success"

        result = failing_operation()

        # Should succeed on third attempt
        assert result == "success"
        assert attempts == 3

        # Verify custom logger was called
        assert custom_logger.debug.called
        # Check that logger.debug was called with retry context
        debug_calls = [str(call) for call in custom_logger.debug.call_args_list]
        assert any("attempt" in call.lower() for call in debug_calls)

    def test_retry_with_custom_logger_async(self):
        """Test that async retry decorator accepts a custom logger parameter."""
        import asyncio

        # Create a custom logger
        custom_logger = Mock(spec=logging.Logger)
        custom_logger.debug = Mock()
        custom_logger.warning = Mock()

        # Track the number of attempts
        attempts = 0

        @retry_transient_errors(max_attempts=3, logger=custom_logger)
        async def failing_operation_async():
            nonlocal attempts
            attempts += 1
            # Raise a transient error on first two attempts
            if attempts < 3:
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
            return "success"

        result = asyncio.run(failing_operation_async())

        # Should succeed on third attempt
        assert result == "success"
        assert attempts == 3

        # Verify custom logger was called
        assert custom_logger.debug.called
        # Check that logger.debug was called with retry context
        debug_calls = [str(call) for call in custom_logger.debug.call_args_list]
        assert any("attempt" in call.lower() for call in debug_calls)

    def test_retry_logs_exception_type_and_attempt_count(self):
        """Test that retry decorator logs exception type and attempt count."""
        custom_logger = Mock(spec=logging.Logger)
        custom_logger.debug = Mock()

        attempts = 0

        @retry_transient_errors(max_attempts=3, logger=custom_logger)
        def failing_operation():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise IOError(errno.EACCES, "Permission denied")
            return "success"

        failing_operation()

        # Verify that logs contain attempt count and exception info
        assert custom_logger.debug.call_count > 0
        first_log = str(custom_logger.debug.call_args_list[0])
        # Should contain attempt information
        assert "attempt" in first_log.lower() or "1/" in first_log

    def test_retry_exhaustion_logs_warning(self):
        """Test that retry decorator logs warning when attempts are exhausted."""
        custom_logger = Mock(spec=logging.Logger)
        custom_logger.warning = Mock()
        custom_logger.debug = Mock()

        @retry_transient_errors(max_attempts=2, logger=custom_logger)
        def always_failing_operation():
            raise IOError(errno.EAGAIN, "Resource temporarily unavailable")

        # Should raise after max attempts
        with pytest.raises(IOError):
            always_failing_operation()

        # Verify warning was logged about exhausted attempts
        assert custom_logger.warning.called
        warning_log = str(custom_logger.warning.call_args)
        assert "max retry" in warning_log.lower() or "exhausted" in warning_log.lower()

    def test_retry_without_logger_uses_default(self):
        """Test that retry decorator works without logger parameter (backward compatibility)."""
        # This should work without errors, using the default module logger
        attempts = 0

        @retry_transient_errors(max_attempts=2)
        def operation_with_default_logger():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
            return "success"

        result = operation_with_default_logger()
        assert result == "success"
        assert attempts == 2

    def test_retry_with_permanent_error_no_retry(self):
        """Test that permanent errors don't trigger retries and are logged."""
        custom_logger = Mock(spec=logging.Logger)
        custom_logger.debug = Mock()

        @retry_transient_errors(max_attempts=3, logger=custom_logger)
        def permanent_error_operation():
            raise IOError(errno.ENOSPC, "No space left on device")

        # Should raise immediately without retries
        with pytest.raises(IOError) as exc_info:
            permanent_error_operation()

        assert exc_info.value.errno == errno.ENOSPC

        # Should log as permanent error
        assert custom_logger.debug.called
        debug_log = str(custom_logger.debug.call_args)
        assert "permanent" in debug_log.lower()
