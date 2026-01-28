"""Test for issue #529 - Verify code is not truncated (False Positive).

This test verifies that the Storage class in src/flywheel/storage.py is complete
and all methods mentioned in the issue exist and are callable.

Issue #529 claimed that the code was truncated at line 234 in the
_get_file_lock_range_from_handle method, missing several methods including:
- _secure_all_parent_directories
- _load
- _cleanup

This test confirms this is a FALSE POSITIVE - all methods exist and work correctly.
"""

import inspect
import os
import tempfile
from pathlib import Path

import pytest

from flywheel import Todo
from flywheel.storage import Storage


class TestIssue529FalsePositive:
    """Verify issue #529 is a false positive - code is complete."""

    def test_storage_class_is_complete(self):
        """Test that Storage class exists and has all expected methods."""
        # Verify Storage class exists
        assert Storage is not None

        # Check for methods mentioned in the issue
        assert hasattr(Storage, '_get_file_lock_range_from_handle')
        assert hasattr(Storage, '_secure_all_parent_directories')
        assert hasattr(Storage, '_load')
        assert hasattr(Storage, '_cleanup')

        # Verify methods are callable
        assert callable(getattr(Storage, '_get_file_lock_range_from_handle'))
        assert callable(getattr(Storage, '_secure_all_parent_directories'))
        assert callable(getattr(Storage, '_load'))
        assert callable(getattr(Storage, '_cleanup'))

    def test_get_file_lock_range_from_handle_complete(self):
        """Test that _get_file_lock_range_from_handle method is complete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.todos"
            storage = Storage(storage_path)

            # Method should exist and be callable
            assert hasattr(storage, '_get_file_lock_range_from_handle')

            # Get the source code of the method
            source = inspect.getsource(storage._get_file_lock_range_from_handle)

            # Verify the method has a complete implementation (not just a comment)
            assert 'def ' in source
            assert 'return' in source
            assert 'if os.name' in source or 'if' in source

            # Verify the method returns expected values
            # Create a dummy file handle for testing
            with open(storage_path, 'w') as f:
                pass

            with open(storage_path, 'r') as f:
                result = storage._get_file_lock_range_from_handle(f)

                # On Windows, should return tuple (0, 1) for 4GB lock
                # On Unix, should return a placeholder value
                if os.name == 'nt':
                    assert result == (0, 1), f"Expected (0, 1) on Windows, got {result}"
                else:
                    # On Unix, returns placeholder (int)
                    assert isinstance(result, int), f"Expected int on Unix, got {type(result)}"

    def test_secure_all_parent_directories_exists(self):
        """Test that _secure_all_parent_directories method exists and works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "subdir" / "test.todos"
            storage = Storage(storage_path)

            # Method should exist
            assert hasattr(storage, '_secure_all_parent_directories')
            assert callable(storage._secure_all_parent_directories)

            # The method is called during __init__, so parent dirs should exist
            assert storage_path.parent.exists()

    def test_load_method_exists(self):
        """Test that _load method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.todos"
            storage = Storage(storage_path)

            # Method should exist
            assert hasattr(storage, '_load')
            assert callable(storage._load)

    def test_cleanup_method_exists(self):
        """Test that _cleanup method exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.todos"
            storage = Storage(storage_path)

            # Method should exist
            assert hasattr(storage, '_cleanup')
            assert callable(storage._cleanup)

    def test_storage_file_end(self):
        """Test that storage.py file ends properly (not truncated)."""
        storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

        # Read the last few lines of the file
        with open(storage_file, 'rb') as f:
            # Seek to end
            f.seek(-500, 2)  # Read last 500 bytes
            end_content = f.read().decode('utf-8')

            # File should end with a class method, not truncated
            # The file ends with the close() method which has 'pass'
            assert 'def close(self)' in end_content or 'class ' in end_content
            assert end_content.rstrip().endswith('pass') or end_content.rstrip().endswith('"""')

    def test_all_storage_methods_callable(self):
        """Test that all critical Storage methods are callable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.todos"
            storage = Storage(storage_path)

            # Test public API methods
            assert callable(storage.add)
            assert callable(storage.get_all)
            assert callable(storage.get)
            assert callable(storage.update)
            assert callable(storage.delete)
            assert callable(storage.get_next_id)
            assert callable(storage.close)

            # Test private methods mentioned in issue
            assert callable(storage._get_file_lock_range_from_handle)
            assert callable(storage._secure_all_parent_directories)
            assert callable(storage._load)
            assert callable(storage._cleanup)

    def test_storage_functional(self):
        """Test that Storage works end-to-end (proving code is complete)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.todos"
            storage = Storage(storage_path)

            # Add a todo
            todo = Todo(title="Test todo", description="Testing issue #529")
            added = storage.add(todo)
            assert added is not None
            assert added.id == 1

            # Retrieve it
            retrieved = storage.get(1)
            assert retrieved is not None
            assert retrieved.title == "Test todo"

            # Update it
            retrieved.title = "Updated todo"
            storage.update(retrieved)

            # Verify update
            updated = storage.get(1)
            assert updated.title == "Updated todo"

            # Delete it
            result = storage.delete(1)
            assert result is True

            # Verify deletion
            deleted = storage.get(1)
            assert deleted is None

    def test_verify_line_234_context(self):
        """Verify the context around line 234 mentioned in the issue."""
        storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

        with open(storage_file, 'r') as f:
            lines = f.readlines()

            # Line 234 (0-indexed: 233) should be within _acquire_file_lock method's docstring
            # It mentions RuntimeError in the Raises section
            line_234 = lines[233].strip()
            assert 'RuntimeError' in line_234 or 'Raises' in line_234 or 'IOError' in line_234

            # The issue claimed code was truncated at an OVERLAPPED comment
            # Let's verify the surrounding context is complete
            context = ''.join(lines[230:240])

            # Should be in the docstring of _acquire_file_lock
            assert 'Raises:' in context or 'IOError' in context
