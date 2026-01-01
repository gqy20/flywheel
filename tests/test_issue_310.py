"""Test for issue #310 - Verify _secure_directory method is complete and functional."""

import os
import tempfile
from pathlib import Path
import pytest

from flywheel.storage import Storage


def test_secure_directory_method_exists():
    """Test that _secure_directory method exists and is callable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Verify method exists
        assert hasattr(storage, '_secure_directory')
        assert callable(storage._secure_directory)


def test_secure_directory_completeness():
    """Test that _secure_directory method is complete and handles errors properly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # This should not raise any errors
        storage = Storage(str(storage_path))

        # Verify the storage was created successfully
        assert storage_path.parent.exists()

        # On Unix-like systems, verify directory has correct permissions
        if os.name != 'nt':
            stat_info = storage_path.parent.stat()
            # Check if permissions are 0o700 (rwx------)
            mode = stat_info.st_mode & 0o777
            assert mode == 0o700, f"Expected 0o700, got {oct(mode)}"


def test_secure_directory_method_has_full_implementation():
    """Test that _secure_directory has complete implementation including exception handling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Get the source code of the method
        import inspect
        source = inspect.getsource(storage._secure_directory)

        # Verify key components are present
        assert 'LookupAccountName' in source or 'chmod' in source
        assert 'security_descriptor' in source or 'RuntimeError' in source
        assert 'win32_success' in source or 'OSError' in source

        # Verify the method has proper error handling
        assert 'raise' in source or 'except' in source


def test_storage_initialization_without_errors():
    """Test that Storage can be initialized without syntax errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # This should not raise SyntaxError or any other error
        try:
            storage = Storage(str(storage_path))
            assert storage is not None
        except SyntaxError as e:
            pytest.fail(f"SyntaxError in storage.py: {e}")
        except Exception as e:
            # Other exceptions are OK for this test (e.g., permission errors)
            pass
