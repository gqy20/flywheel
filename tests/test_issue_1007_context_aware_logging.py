"""Tests for Issue #1007 - Context-aware logging in measure_latency decorator.

ISSUE #1007 requests that the measure_latency decorator inspect function arguments
for 'path' or 'id' parameters and include them in log messages for easier debugging.

This test verifies that:
1. Functions with 'path' parameter include path in log message
2. Functions with 'id' parameter include id in log message
3. Functions without path/id still work (backward compatibility)
4. Both sync and async functions are supported
5. Works with both positional and keyword arguments
"""

import pytest
from unittest.mock import patch
from flywheel.storage import measure_latency


class TestContextAwareLoggingWithPath:
    """Test that measure_latency includes 'path' parameter in log messages."""

    def test_sync_function_with_path_positional(self):
        """Test sync function with path as positional argument."""
        @measure_latency("test_operation")
        def mock_save_operation(path):
            return f"saved to {path}"

        # Mock logger to capture log calls
        with patch('flywheel.storage.logger') as mock_logger:
            result = mock_save_operation("/tmp/test.json")

            # Verify function works
            assert result == "saved to /tmp/test.json"

            # Verify logger was called with context
            mock_logger.debug.assert_called()
            call_args = mock_logger.debug.call_args[0][0]
            assert "/tmp/test.json" in call_args, \
                f"Log message should include path, got: {call_args}"
            assert "test_operation" in call_args
            assert "completed in" in call_args

    def test_sync_function_with_path_keyword(self):
        """Test sync function with path as keyword argument."""
        @measure_latency("load")
        def mock_load(path="/default/path"):
            return f"loaded from {path}"

        with patch('flywheel.storage.logger') as mock_logger:
            result = mock_load(path="/custom/path.json")

            assert result == "loaded from /custom/path.json"

            mock_logger.debug.assert_called()
            call_args = mock_logger.debug.call_args[0][0]
            assert "/custom/path.json" in call_args, \
                f"Log message should include path, got: {call_args}"

    def test_async_function_with_path(self):
        """Test async function with path parameter."""
        import asyncio

        @measure_latency("async_save")
        async def mock_async_save(path):
            await asyncio.sleep(0.01)  # Simulate I/O
            return f"async saved to {path}"

        async def run_test():
            with patch('flywheel.storage.logger') as mock_logger:
                result = await mock_async_save("/tmp/async_test.json")

                assert result == "async saved to /tmp/async_test.json"

                mock_logger.debug.assert_called()
                call_args = mock_logger.debug.call_args[0][0]
                assert "/tmp/async_test.json" in call_args, \
                    f"Log message should include path, got: {call_args}"

        asyncio.run(run_test())


class TestContextAwareLoggingWithId:
    """Test that measure_latency includes 'id' parameter in log messages."""

    def test_sync_function_with_id(self):
        """Test sync function with id parameter."""
        @measure_latency("fetch")
        def mock_fetch(id):
            return f"fetched item {id}"

        with patch('flywheel.storage.logger') as mock_logger:
            result = mock_fetch(12345)

            assert result == "fetched item 12345"

            mock_logger.debug.assert_called()
            call_args = mock_logger.debug.call_args[0][0]
            assert "12345" in call_args, \
                f"Log message should include id, got: {call_args}"

    def test_async_function_with_id(self):
        """Test async function with id parameter."""
        import asyncio

        @measure_latency("async_fetch")
        async def mock_async_fetch(id):
            await asyncio.sleep(0.01)
            return f"async fetched {id}"

        async def run_test():
            with patch('flywheel.storage.logger') as mock_logger:
                result = await mock_async_fetch(67890)

                assert result == "async fetched 67890"

                mock_logger.debug.assert_called()
                call_args = mock_logger.debug.call_args[0][0]
                assert "67890" in call_args, \
                    f"Log message should include id, got: {call_args}"

        asyncio.run(run_test())


class TestBackwardCompatibility:
    """Test that functions without path/id still work (backward compatibility)."""

    def test_function_without_path_or_id(self):
        """Test function with no path or id parameter."""
        @measure_latency("generic_operation")
        def mock_operation():
            return "operation complete"

        with patch('flywheel.storage.logger') as mock_logger:
            result = mock_operation()

            assert result == "operation complete"

            mock_logger.debug.assert_called()
            call_args = mock_logger.debug.call_args[0][0]
            # Should log timing but without context
            assert "generic_operation" in call_args
            assert "completed in" in call_args
            assert "ms" in call_args

    def test_function_with_other_parameters(self):
        """Test function with parameters other than path/id."""
        @measure_latency("process")
        def mock_process(data, options):
            return f"processed {data} with {options}"

        with patch('flywheel.storage.logger') as mock_logger:
            result = mock_process("my_data", {"opt": "value"})

            assert result == "processed my_data with {'opt': 'value'}"

            mock_logger.debug.assert_called()
            call_args = mock_logger.debug.call_args[0][0]
            # Should log timing but without specific context
            assert "process" in call_args
            assert "completed in" in call_args


class TestPriorityPrecedence:
    """Test priority when both path and id are present."""

    def test_path_takes_precedence_over_id(self):
        """Test that path is preferred when both path and id exist."""
        @measure_latency("save_with_id")
        def mock_save_with_id(path, id):
            return f"saved {path} with id {id}"

        with patch('flywheel.storage.logger') as mock_logger:
            result = mock_save_with_id("/tmp/test.json", 999)

            assert result == "saved /tmp/test.json with id 999"

            mock_logger.debug.assert_called()
            call_args = mock_logger.debug.call_args[0][0]
            # Should include path (preferred over id)
            assert "/tmp/test.json" in call_args, \
                f"Log message should include path, got: {call_args}"


def test_issue_1007_logging_format():
    """Test that log format includes operation name and timing."""
    @measure_latency("test_op")
    def test_func():
        return "done"

    with patch('flywheel.storage.logger') as mock_logger:
        test_func()

        call_args = mock_logger.debug.call_args[0][0]
        # Verify format: "{operation} on {path/id} completed in {elapsed}ms"
        # or "{operation} completed in {elapsed}ms" if no context
        assert "test_op" in call_args
        assert "completed in" in call_args
        assert "ms" in call_args
        # Should contain either "on {context}" or just "completed in"
        # This will be verified by the actual implementation
