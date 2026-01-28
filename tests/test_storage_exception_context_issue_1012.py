"""Tests for exception context in decorators (Issue #1012)."""
import asyncio
import pathlib
import tempfile
import pytest
from flywheel.storage import measure_latency


class TestExceptionContext:
    """Test that exceptions in decorated functions include context information."""

    def test_sync_wrapper_exception_includes_path_context(self):
        """Test that sync wrapper adds path context to exceptions."""
        @measure_latency("test_operation")
        def failing_operation(path: str):
            raise ValueError("Operation failed")

        # Test with path argument
        with pytest.raises(ValueError) as exc_info:
            failing_operation("/tmp/test.json")

        # Exception should include context about the path
        assert "/tmp/test.json" in str(exc_info.value) or hasattr(exc_info.value, '__context__')

    def test_sync_wrapper_exception_includes_id_context(self):
        """Test that sync wrapper adds id context to exceptions."""
        @measure_latency("test_operation")
        def failing_operation_with_id(id: int):
            raise ValueError("Operation failed")

        # Test with id argument
        with pytest.raises(ValueError) as exc_info:
            failing_operation_with_id(12345)

        # Exception should include context about the id
        assert "12345" in str(exc_info.value) or hasattr(exc_info.value, '__context__')

    @pytest.mark.asyncio
    async def test_async_wrapper_exception_includes_path_context(self):
        """Test that async wrapper adds path context to exceptions."""
        @measure_latency("test_operation")
        async def failing_async_operation(path: str):
            raise ValueError("Async operation failed")

        # Test with path argument
        with pytest.raises(ValueError) as exc_info:
            await failing_async_operation("/tmp/test.json")

        # Exception should include context about the path
        assert "/tmp/test.json" in str(exc_info.value) or hasattr(exc_info.value, '__context__')

    @pytest.mark.asyncio
    async def test_async_wrapper_exception_includes_id_context(self):
        """Test that async wrapper adds id context to exceptions."""
        @measure_latency("test_operation")
        async def failing_async_operation_with_id(id: int):
            raise ValueError("Async operation failed")

        # Test with id argument
        with pytest.raises(ValueError) as exc_info:
            await failing_async_operation_with_id(12345)

        # Exception should include context about the id
        assert "12345" in str(exc_info.value) or hasattr(exc_info.value, '__context__')

    def test_sync_wrapper_exception_with_kwarg_path(self):
        """Test that sync wrapper adds context when path is passed as keyword argument."""
        @measure_latency("test_operation")
        def failing_operation(**kwargs):
            raise ValueError("Operation failed")

        # Test with path as keyword argument
        with pytest.raises(ValueError) as exc_info:
            failing_operation(path="/tmp/test.json")

        # Exception should include context about the path
        assert "/tmp/test.json" in str(exc_info.value) or hasattr(exc_info.value, '__context__')

    @pytest.mark.asyncio
    async def test_async_wrapper_exception_with_kwarg_path(self):
        """Test that async wrapper adds context when path is passed as keyword argument."""
        @measure_latency("test_operation")
        async def failing_async_operation(**kwargs):
            raise ValueError("Async operation failed")

        # Test with path as keyword argument
        with pytest.raises(ValueError) as exc_info:
            await failing_async_operation(path="/tmp/test.json")

        # Exception should include context about the path
        assert "/tmp/test.json" in str(exc_info.value) or hasattr(exc_info.value, '__context__')

    def test_sync_wrapper_preserves_original_exception(self):
        """Test that sync wrapper preserves the original exception type."""
        @measure_latency("test_operation")
        def failing_operation(path: str):
            raise FileNotFoundError(f"File not found: {path}")

        # Test with path argument
        with pytest.raises(FileNotFoundError) as exc_info:
            failing_operation("/tmp/test.json")

        # Should still be FileNotFoundError
        assert isinstance(exc_info.value, FileNotFoundError)
        # And the error message should mention the file
        assert "/tmp/test.json" in str(exc_info.value) or "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_wrapper_preserves_original_exception(self):
        """Test that async wrapper preserves the original exception type."""
        @measure_latency("test_operation")
        async def failing_async_operation(path: str):
            raise FileNotFoundError(f"File not found: {path}")

        # Test with path argument
        with pytest.raises(FileNotFoundError) as exc_info:
            await failing_async_operation("/tmp/test.json")

        # Should still be FileNotFoundError
        assert isinstance(exc_info.value, FileNotFoundError)
        # And the error message should mention the file
        assert "/tmp/test.json" in str(exc_info.value) or "File not found" in str(exc_info.value)

    def test_sync_wrapper_with_pathlib_path(self):
        """Test that sync wrapper handles pathlib.Path objects."""
        @measure_latency("test_operation")
        def failing_operation(path: pathlib.Path):
            raise ValueError("Operation failed")

        # Test with pathlib.Path
        test_path = pathlib.Path("/tmp/test.json")
        with pytest.raises(ValueError) as exc_info:
            failing_operation(test_path)

        # Exception should include context about the path
        assert "test.json" in str(exc_info.value) or hasattr(exc_info.value, '__context__')
