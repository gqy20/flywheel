"""
Test for issue #1759: Syntax error with raise statement in storage.py
"""
import pytest
import tempfile
from pathlib import Path
from flywheel.storage import local_file


def test_async_file_close_exception_propagation():
    """
    Test that when an exception occurs during file close in async context manager,
    it is properly propagated when there's no other exception.

    This test verifies the fix for the syntax error at line 114 of storage.py
    where 'raise' should be 'raise close_exc'.
    """
    async def test_close_exception():
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write("test content")

        try:
            # Mock a file that will raise an exception on close
            original_close = None

            async with local_file(tmp_path, 'r') as f:
                # Store original close method
                original_close = f._file.close

                # Replace close with a function that raises an exception
                def failing_close():
                    raise IOError("Failed to close file")

                f._file.close = failing_close

                # Read the file to ensure it's open
                content = await f.read()
                assert content == "test content"

            # The exception from close should be propagated
            pytest.fail("Expected IOError from close to be raised")
        except IOError as e:
            # This is expected - the close exception should propagate
            assert str(e) == "Failed to close file"
        finally:
            # Cleanup
            if tmp_path.exists():
                tmp_path.unlink()

    # Run the async test
    import asyncio
    asyncio.run(test_close_exception())


def test_async_file_close_exception_with_context_exception():
    """
    Test that when both a context exception and close exception occur,
    the context exception is preserved and close exception is logged.

    This is the complementary case to the above test.
    """
    async def test_context_exception_takes_precedence():
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write("test content")

        try:
            async with local_file(tmp_path, 'r') as f:
                # Replace close with a function that raises an exception
                def failing_close():
                    raise IOError("Failed to close file")

                f._file.close = failing_close

                # Raise an exception in the context body
                raise ValueError("Context body error")
        except ValueError as e:
            # The context exception should be raised, not the close exception
            assert str(e) == "Context body error"
        finally:
            # Cleanup
            if tmp_path.exists():
                tmp_path.unlink()

    # Run the async test
    import asyncio
    asyncio.run(test_context_exception_takes_precedence())
