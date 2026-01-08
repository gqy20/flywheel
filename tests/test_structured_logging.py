"""Tests for structured logging context in I/O operations (Issue #1042)."""
import logging
import pytest
import errno
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestStructuredLoggingContext:
    """Test that I/O operations include structured logging context."""

    @pytest.mark.asyncio
    async def test_retry_io_operation_creates_logger_adapter_with_context(self, tmp_path):
        """Test that _retry_io_operation creates LoggerAdapter with path and operation context."""
        from flywheel.storage import _retry_io_operation

        # Create a test file
        test_file = tmp_path / "test_log_context.txt"
        test_file.write_text("test content")

        # Mock the LoggerAdapter to verify it's called with correct context
        with patch('flywheel.storage.logging.LoggerAdapter') as mock_adapter:
            # Configure mock to return a logger that records calls
            mock_logger_instance = MagicMock()
            mock_adapter.return_value = mock_logger_instance

            # Perform a read operation
            async def read_operation():
                with open(test_file, 'r') as f:
                    return f.read()

            result = await _retry_io_operation(
                read_operation,
                operation_type='read',
                path=str(test_file)
            )

            # Verify LoggerAdapter was created with correct extra context
            assert mock_adapter.called, "LoggerAdapter should be created when path and operation_type are provided"
            call_args = mock_adapter.call_args
            extra_context = call_args[0][1]  # Second positional arg is the extra dict

            assert 'path' in extra_context, "Extra context should include 'path'"
            assert extra_context['path'] == str(test_file), f"Path should be {test_file}"
            assert 'operation' in extra_context, "Extra context should include 'operation'"
            assert extra_context['operation'] == 'read', "Operation should be 'read'"
            assert result == "test content"

    @pytest.mark.asyncio
    async def test_retry_io_operation_write_context(self, tmp_path):
        """Test that write operations include proper logging context."""
        from flywheel.storage import _retry_io_operation

        # Create a test file
        test_file = tmp_path / "test_write_context.txt"

        with patch('flywheel.storage.logging.LoggerAdapter') as mock_adapter:
            # Configure mock to return a logger
            mock_logger_instance = MagicMock()
            mock_adapter.return_value = mock_logger_instance

            # Perform a write operation
            async def write_operation():
                with open(test_file, 'w') as f:
                    f.write("test write")

            await _retry_io_operation(
                write_operation,
                operation_type='write',
                path=str(test_file)
            )

            # Verify LoggerAdapter was created with write context
            assert mock_adapter.called
            extra_context = mock_adapter.call_args[0][1]

            assert extra_context['operation'] == 'write', "Operation should be 'write'"
            assert extra_context['path'] == str(test_file), f"Path should be {test_file}"
            assert test_file.read_text() == "test write"

    @pytest.mark.asyncio
    async def test_retry_with_transient_error_logs_with_context(self, tmp_path):
        """Test that retry logs after transient errors include operation context."""
        from flywheel.storage import _retry_io_operation

        # Create a test file
        test_file = tmp_path / "test_retry_context.txt"
        test_file.write_text("test")

        with patch('flywheel.storage.logging.LoggerAdapter') as mock_adapter:
            # Create a real mock logger that records calls
            mock_logger_instance = MagicMock()
            mock_adapter.return_value = mock_logger_instance

            # Create an operation that fails once with EIO then succeeds
            call_count = [0]

            async def flaky_operation():
                call_count[0] += 1
                if call_count[0] == 1:
                    # Simulate transient I/O error
                    err = IOError("Transient error")
                    err.errno = errno.EIO
                    raise err
                # Success on second try
                with open(test_file, 'r') as f:
                    return f.read()

            result = await _retry_io_operation(
                flaky_operation,
                operation_type='read',
                path=str(test_file),
                max_attempts=3
            )

            # Verify LoggerAdapter was created
            assert mock_adapter.called
            extra_context = mock_adapter.call_args[0][1]

            # Verify context was passed correctly
            assert extra_context['operation'] == 'read'
            assert extra_context['path'] == str(test_file)

            # Verify the adapter's debug method was called for retry logging
            assert mock_logger_instance.debug.called, "Logger should log debug message about retry"

            # Get the log message
            log_call_args = mock_logger_instance.debug.call_args[0][0]
            assert 'retrying' in log_call_args.lower() or 'error' in log_call_args.lower(), \
                f"Expected retry log message, got: {log_call_args}"

            assert result == "test"

    @pytest.mark.asyncio
    async def test_retry_without_context_does_not_create_adapter(self, tmp_path):
        """Test that _retry_io_operation without path/operation doesn't create LoggerAdapter."""
        from flywheel.storage import _retry_io_operation

        test_file = tmp_path / "test_no_context.txt"
        test_file.write_text("test")

        with patch('flywheel.storage.logging.LoggerAdapter') as mock_adapter:
            async def simple_operation():
                with open(test_file, 'r') as f:
                    return f.read()

            result = await _retry_io_operation(
                simple_operation
                # No path or operation_type provided
            )

            # LoggerAdapter should NOT be created when no context is provided
            assert not mock_adapter.called, "LoggerAdapter should not be created without context"
            assert result == "test"
