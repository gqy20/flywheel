"""Tests for exception chain preservation (Issue #1016).

This test verifies that:
1. Original exception stack trace is preserved in the exception chain
2. The __cause__ attribute is properly set and accessible
3. The exception chain is visible in formatted tracebacks
"""
import asyncio
import traceback
import pytest
from flywheel.storage import measure_latency


class TestExceptionChainPreservation:
    """Test that exception chains are properly preserved and accessible."""

    def test_sync_wrapper_preserves_exception_chain(self):
        """Test that sync wrapper preserves the complete exception chain."""
        @measure_latency("test_operation")
        def failing_operation(path: str):
            # Raise an exception with its own cause
            try:
                raise ValueError("Inner error")
            except ValueError as inner:
                raise RuntimeError(f"Outer error for {path}") from inner

        # Test that the exception chain is preserved
        with pytest.raises(RuntimeError) as exc_info:
            failing_operation("/tmp/test.json")

        # Check that __cause__ is set
        assert exc_info.value.__cause__ is not None
        # Check that the original exception is in the chain
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert str(exc_info.value.__cause__) == "Inner error"
        # Check that context is added to the exception message
        assert "/tmp/test.json" in str(exc_info.value)

    def test_sync_wrapper_exception_chain_in_traceback(self):
        """Test that the exception chain appears in formatted tracebacks."""
        @measure_latency("test_operation")
        def failing_operation(path: str):
            try:
                raise ValueError("Deep inner error")
            except ValueError as inner:
                raise RuntimeError(f"Operation failed on {path}") from inner

        with pytest.raises(RuntimeError) as exc_info:
            failing_operation("/tmp/test.json")

        # Format the exception and verify the chain is visible
        formatted = traceback.format_exception(type(exc_info.value), exc_info.value, exc_info.tb)
        formatted_text = ''.join(formatted)

        # The chain should be visible in the traceback
        # Either explicitly or through the exception message
        assert "Deep inner error" in formatted_text or "Inner error" in str(exc_info.value.__cause__)

    def test_sync_wrapper_handles_builtin_exceptions(self):
        """Test that sync wrapper properly handles built-in exceptions with specific constructors."""
        @measure_latency("test_operation")
        def failing_operation(path: str):
            # TypeError can be particular about its arguments
            raise TypeError("Invalid type")

        with pytest.raises(TypeError) as exc_info:
            failing_operation("/tmp/test.json")

        # Should still be TypeError
        assert isinstance(exc_info.value, TypeError)
        # The error message should be preserved
        assert "Invalid type" in str(exc_info.value)

    def test_sync_wrapper_no_double_exception_creation(self):
        """Test that we don't create exceptions that can't be instantiated."""
        @measure_latency("test_operation")
        def failing_operation(path: str):
            # Some exceptions like StopIteration require specific arguments
            raise StopIteration("Stopped")

        with pytest.raises(StopIteration) as exc_info:
            failing_operation("/tmp/test.json")

        # Should still be StopIteration
        assert isinstance(exc_info.value, StopIteration)

    @pytest.mark.asyncio
    async def test_async_wrapper_preserves_exception_chain(self):
        """Test that async wrapper preserves the complete exception chain."""
        @measure_latency("test_operation")
        async def failing_async_operation(path: str):
            # Raise an exception with its own cause
            try:
                raise ValueError("Inner async error")
            except ValueError as inner:
                raise RuntimeError(f"Outer async error for {path}") from inner

        # Test that the exception chain is preserved
        with pytest.raises(RuntimeError) as exc_info:
            await failing_async_operation("/tmp/test.json")

        # Check that __cause__ is set
        assert exc_info.value.__cause__ is not None
        # Check that the original exception is in the chain
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert str(exc_info.value.__cause__) == "Inner async error"
        # Check that context is added to the exception message
        assert "/tmp/test.json" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_wrapper_exception_chain_in_traceback(self):
        """Test that the exception chain appears in formatted tracebacks for async functions."""
        @measure_latency("test_operation")
        async def failing_async_operation(path: str):
            try:
                raise ValueError("Deep inner async error")
            except ValueError as inner:
                raise RuntimeError(f"Async operation failed on {path}") from inner

        with pytest.raises(RuntimeError) as exc_info:
            await failing_async_operation("/tmp/test.json")

        # Format the exception and verify the chain is visible
        formatted = traceback.format_exception(type(exc_info.value), exc_info.value, exc_info.tb)
        formatted_text = ''.join(formatted)

        # The chain should be visible in the traceback
        assert "Deep inner async error" in formatted_text or "Inner async error" in str(exc_info.value.__cause__)

    @pytest.mark.asyncio
    async def test_async_wrapper_handles_builtin_exceptions(self):
        """Test that async wrapper properly handles built-in exceptions with specific constructors."""
        @measure_latency("test_operation")
        async def failing_async_operation(path: str):
            raise TypeError("Invalid async type")

        with pytest.raises(TypeError) as exc_info:
            await failing_async_operation("/tmp/test.json")

        # Should still be TypeError
        assert isinstance(exc_info.value, TypeError)
        # The error message should be preserved
        assert "Invalid async type" in str(exc_info.value)
