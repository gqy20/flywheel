"""
Test for aiofiles fallback functionality (Issue #1032)

This test ensures that when aiofiles is not available, the storage module
can still function by falling back to synchronous file operations using
asyncio.to_thread.
"""

import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

# Test that storage can handle missing aiofiles
def test_storage_module_handles_missing_aiofiles():
    """
    Test that when aiofiles is not available, the module can still be imported
    and provides appropriate fallback behavior.
    """
    # Mock the import of aiofiles to raise ImportError
    import_context = {}

    with patch.dict('sys.modules', {'aiofiles': None}):
        # Remove aiofiles from sys.modules if it was already imported
        aiofiles_backup = sys.modules.get('aiofiles')
        if 'aiofiles' in sys.modules:
            del sys.modules['aiofiles']

        try:
            # Re-import the storage module without aiofiles available
            if 'flywheel.storage' in sys.modules:
                del sys.modules['flywheel.storage']

            # This should not raise an ImportError
            from flywheel import storage

            # Verify that the module was imported successfully
            assert storage is not None

            # Check if HAS_AIOFILES flag is defined and set to False
            assert hasattr(storage, 'HAS_AIOFILES')
            assert storage.HAS_AIOFILES is False

        finally:
            # Restore aiofiles module
            if aiofiles_backup is not None:
                sys.modules['aiofiles'] = aiofiles_backup


@pytest.mark.asyncio
async def test_storage_operations_without_aiofiles():
    """
    Test that async storage operations work even when aiofiles is not available,
    by falling back to asyncio.to_thread with built-in open.
    """
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.json"

        # Mock aiofiles as unavailable
        aiofiles_backup = sys.modules.get('aiofiles')
        if 'aiofiles' in sys.modules:
            del sys.modules['aiofiles']

        try:
            # Re-import storage module without aiofiles
            if 'flywheel.storage' in sys.modules:
                del sys.modules['flywheel.storage']

            from flywheel.storage import JsonStorage

            # Create a JsonStorage instance
            storage_obj = JsonStorage(test_file)

            # Test write operation
            test_data = {"test": "data", "number": 42}
            await storage_obj._save(test_data)

            # Verify the file was written
            assert test_file.exists()

            # Test read operation
            loaded_data = await storage_obj._load()
            assert loaded_data == test_data

        finally:
            # Restore aiofiles module
            if aiofiles_backup is not None:
                sys.modules['aiofiles'] = aiofiles_backup


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
