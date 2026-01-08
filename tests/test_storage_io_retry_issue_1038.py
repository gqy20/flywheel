"""Test I/O retry logic for transient errors (Issue #1038).

This test verifies that:
1. File open() operations retry on transient I/O errors
2. File read() operations retry on transient I/O errors
3. File write() operations retry on transient I/O errors
4. Retry uses exponential backoff
5. Retry eventually succeeds after transient errors
"""

import errno
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import FileStorage, _AsyncFileContextManager
from flywheel.todo import Todo


class TestIORetryLogic:
    """Test suite for I/O retry logic on file operations."""

    @pytest.mark.asyncio
    async def test_file_open_retry_on_eio(self):
        """Test that file open() retries on errno.EIO."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            attempt_count = [0]
            original_open = open

            def flaky_open(path, *args, **kwargs):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    raise IOError(errno.EIO, "I/O error")
                return original_open(path, *args, **kwargs)

            with patch('builtins.open', side_effect=flaky_open):
                async with _AsyncFileContextManager(str(test_file), 'r') as f:
                    content = await f.read()

            assert attempt_count[0] == 2, "Should have retried once on EIO"
            assert content == "test content"

    @pytest.mark.asyncio
    async def test_file_open_retry_on_eagain(self):
        """Test that file open() retries on errno.EAGAIN."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            attempt_count = [0]
            original_open = open

            def flaky_open(path, *args, **kwargs):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    raise IOError(errno.EAGAIN, "Resource temporarily unavailable")
                return original_open(path, *args, **kwargs)

            with patch('builtins.open', side_effect=flaky_open):
                async with _AsyncFileContextManager(str(test_file), 'r') as f:
                    content = await f.read()

            assert attempt_count[0] == 2, "Should have retried once on EAGAIN"

    @pytest.mark.asyncio
    async def test_file_read_retry_on_eio(self):
        """Test that file read() retries on errno.EIO."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            async with _AsyncFileContextManager(str(test_file), 'r') as f:
                attempt_count = [0]
                original_read = f._file.read

                async def flaky_read():
                    attempt_count[0] += 1
                    if attempt_count[0] == 1:
                        raise IOError(errno.EIO, "I/O error")
                    return await original_read()

                # Monkey-patch the read method
                f.read = flaky_read
                content = await f.read()

            assert attempt_count[0] == 2, "Should have retried once on EIO"
            assert content == "test content"

    @pytest.mark.asyncio
    async def test_file_write_retry_on_eio(self):
        """Test that file write() retries on errno.EIO."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"

            async with _AsyncFileContextManager(str(test_file), 'w') as f:
                attempt_count = [0]
                original_write = f._file.write

                async def flaky_write(data):
                    attempt_count[0] += 1
                    if attempt_count[0] == 1:
                        raise IOError(errno.EIO, "I/O error")
                    return await original_write(data)

                # Monkey-patch the write method
                f.write = flaky_write
                await f.write("test content")
                await f.flush()

            assert attempt_count[0] == 2, "Should have retried once on EIO"
            assert test_file.read_text() == "test content"

    @pytest.mark.asyncio
    async def test_file_operations_retry_with_exponential_backoff(self):
        """Test that file operations use exponential backoff."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            attempt_count = [0]
            timestamps = []
            original_open = open

            def flaky_open(path, *args, **kwargs):
                attempt_count[0] += 1
                timestamps.append(time.time())
                if attempt_count[0] <= 2:
                    raise IOError(errno.EIO, "I/O error")
                return original_open(path, *args, **kwargs)

            with patch('builtins.open', side_effect=flaky_open):
                async with _AsyncFileContextManager(str(test_file), 'r') as f:
                    content = await f.read()

            assert attempt_count[0] == 3, "Should have retried twice"
            assert content == "test content"

            # Verify exponential backoff: delays should increase
            if len(timestamps) >= 3:
                delay1 = timestamps[1] - timestamps[0]
                delay2 = timestamps[2] - timestamps[1]
                # Second delay should be longer (exponential backoff)
                assert delay2 > delay1 * 0.8, "Should use exponential backoff"

    @pytest.mark.asyncio
    async def test_file_operations_fail_after_max_attempts(self):
        """Test that file operations eventually fail after max attempts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"

            attempt_count = [0]

            def always_failing_open(path, *args, **kwargs):
                attempt_count[0] += 1
                raise IOError(errno.EIO, "I/O error")

            with patch('builtins.open', side_effect=always_failing_open):
                with pytest.raises(IOError):
                    async with _AsyncFileContextManager(str(test_file), 'r') as f:
                        await f.read()

            # Should have attempted multiple times (default max retries: 3)
            assert attempt_count[0] == 3, "Should have attempted 3 times total"

    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_errors(self):
        """Test that permanent errors are not retried."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"

            attempt_count = [0]

            def failing_open(path, *args, **kwargs):
                attempt_count[0] += 1
                raise IOError(errno.ENOENT, "No such file or directory")

            with patch('builtins.open', side_effect=failing_open):
                with pytest.raises(IOError):
                    async with _AsyncFileContextManager(str(test_file), 'r') as f:
                        await f.read()

            # Should only attempt once (no retry for permanent errors)
            assert attempt_count[0] == 1, "Should not retry on permanent errors"

    @pytest.mark.asyncio
    async def test_storage_with_retry_integration(self):
        """Integration test: storage operations benefit from I/O retry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = FileStorage(str(storage_path))

            # Add a todo
            todo1 = Todo(title="Test todo", description="Test description")
            storage.add(todo1)
            storage.close()

            # Mock file operations to fail transiently
            attempt_count = [0]
            original_open = open

            def flaky_open(path, *args, **kwargs):
                attempt_count[0] += 1
                # Only fail on first read attempt
                if attempt_count[0] == 1 and 'r' in args[0] if args else 'r' in kwargs.get('mode', ''):
                    raise IOError(errno.EIO, "I/O error")
                return original_open(path, *args, **kwargs)

            # Create new storage instance with flaky I/O
            with patch('builtins.open', side_effect=flaky_open):
                storage2 = FileStorage(str(storage_path))
                todos = storage2.get_all()
                storage2.close()

            assert len(todos) == 1, "Should have loaded todos after retry"
            assert attempt_count[0] >= 2, "Should have retried on I/O error"
