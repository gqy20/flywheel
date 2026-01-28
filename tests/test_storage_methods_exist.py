"""Test to verify FileStorage class has all required methods (Issue #681).

This test verifies that the FileStorage class is complete and not truncated.
It checks that all methods mentioned in the issue are properly defined.
"""

import inspect
import pytest
from flywheel.storage import FileStorage


class TestFileStorageMethodsExist:
    """Verify FileStorage class has all required methods."""

    def test_filestorage_class_exists(self):
        """Test that FileStorage class exists."""
        assert FileStorage is not None
        assert inspect.isclass(FileStorage)

    def test_filestorage_has_add_method(self):
        """Test that FileStorage has add method."""
        assert hasattr(FileStorage, 'add')
        assert callable(getattr(FileStorage, 'add'))

    def test_filestorage_has_list_method(self):
        """Test that FileStorage has list method."""
        assert hasattr(FileStorage, 'list')
        assert callable(getattr(FileStorage, 'list'))

    def test_filestorage_has_update_method(self):
        """Test that FileStorage has update method."""
        assert hasattr(FileStorage, 'update')
        assert callable(getattr(FileStorage, 'update'))

    def test_filestorage_has_delete_method(self):
        """Test that FileStorage has delete method."""
        assert hasattr(FileStorage, 'delete')
        assert callable(getattr(FileStorage, 'delete'))

    def test_filestorage_has_get_next_id_method(self):
        """Test that FileStorage has get_next_id method."""
        assert hasattr(FileStorage, 'get_next_id')
        assert callable(getattr(FileStorage, 'get_next_id'))

    def test_filestorage_has_add_batch_method(self):
        """Test that FileStorage has add_batch method."""
        assert hasattr(FileStorage, 'add_batch')
        assert callable(getattr(FileStorage, 'add_batch'))

    def test_filestorage_has_update_batch_method(self):
        """Test that FileStorage has update_batch method."""
        assert hasattr(FileStorage, 'update_batch')
        assert callable(getattr(FileStorage, 'update_batch'))

    def test_filestorage_has_health_check_method(self):
        """Test that FileStorage has health_check method."""
        assert hasattr(FileStorage, 'health_check')
        assert callable(getattr(FileStorage, 'health_check'))

    def test_filestorage_all_methods_signatures(self):
        """Test that all methods have correct signatures."""
        # Check add method signature
        add_sig = inspect.signature(FileStorage.add)
        assert 'todo' in add_sig.parameters

        # Check list method signature
        list_sig = inspect.signature(FileStorage.list)
        assert 'status' in list_sig.parameters

        # Check update method signature
        update_sig = inspect.signature(FileStorage.update)
        assert 'todo' in update_sig.parameters

        # Check delete method signature
        delete_sig = inspect.signature(FileStorage.delete)
        assert 'todo_id' in delete_sig.parameters

        # Check add_batch method signature
        add_batch_sig = inspect.signature(FileStorage.add_batch)
        assert 'todos' in add_batch_sig.parameters

        # Check update_batch method signature
        update_batch_sig = inspect.signature(FileStorage.update_batch)
        assert 'todos' in update_batch_sig.parameters
