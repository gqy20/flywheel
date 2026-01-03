"""Test storage abstraction layer (issue #568)."""

import pytest
from abc import ABC, abstractmethod
from flywheel.storage import Storage, FileStorage


class TestAbstractStorageExists:
    """Test that AbstractStorage abstract base class exists."""

    def test_abstract_storage_class_exists(self):
        """AbstractStorage class should be importable and be an ABC."""
        from flywheel.storage import AbstractStorage

        # Should be an abstract base class
        assert issubclass(AbstractStorage, ABC)
        assert hasattr(AbstractStorage, '__abstractmethods__')

    def test_abstract_storage_has_required_methods(self):
        """AbstractStorage should define abstract methods for storage operations."""
        from flywheel.storage import AbstractStorage

        # Check that abstract methods exist
        abstract_methods = AbstractStorage.__abstractmethods__

        required_methods = {'add', 'list', 'get', 'update', 'delete', 'get_next_id'}
        assert required_methods.issubset(abstract_methods), \
            f"Missing abstract methods: {required_methods - abstract_methods}"


class TestFileStorageInheritsFromAbstract:
    """Test that FileStorage inherits from AbstractStorage."""

    def test_file_storage_exists(self):
        """FileStorage class should be importable."""
        # Should be able to import without error
        from flywheel.storage import FileStorage
        assert FileStorage is not None

    def test_file_storage_inherits_from_abstract_storage(self):
        """FileStorage should inherit from AbstractStorage."""
        from flywheel.storage import FileStorage, AbstractStorage

        assert issubclass(FileStorage, AbstractStorage)

    def test_file_storage_implements_abstract_methods(self):
        """FileStorage should implement all abstract methods from AbstractStorage."""
        from flywheel.storage import FileStorage, AbstractStorage

        # FileStorage should not have any unimplemented abstract methods
        assert len(FileStorage.__abstractmethods__) == 0, \
            f"FileStorage has unimplemented abstract methods: {FileStorage.__abstractmethods__}"

    def test_file_storage_can_be_instantiated(self):
        """FileStorage should be instantiable with a path argument."""
        from flywheel.storage import FileStorage
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/todos.json"
            storage = FileStorage(storage_path)
            assert storage is not None
            assert isinstance(storage, FileStorage)


class TestStorageBackwardCompatibility:
    """Test that old Storage class still works for backward compatibility."""

    def test_storage_class_exists(self):
        """Storage class should still exist for backward compatibility."""
        from flywheel.storage import Storage
        assert Storage is not None

    def test_storage_is_alias_to_file_storage(self):
        """Storage should be an alias to FileStorage for backward compatibility."""
        from flywheel.storage import Storage, FileStorage

        # Storage should either be FileStorage or inherit from it
        # This allows existing code to continue working
        assert Storage is FileStorage or issubclass(Storage, FileStorage)

    def test_storage_can_be_instantiated(self):
        """Storage should still be instantiable with default arguments."""
        from flywheel.storage import Storage
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/todos.json"
            storage = Storage(storage_path)
            assert storage is not None


class TestAbstractStorageInterface:
    """Test that AbstractStorage defines the correct interface."""

    def test_add_method_signature(self):
        """AbstractStorage.add should have the correct signature."""
        from flywheel.storage import AbstractStorage
        import inspect

        sig = inspect.signature(AbstractStorage.add)
        params = list(sig.parameters.keys())

        assert 'self' in params
        assert 'todo' in params

    def test_list_method_signature(self):
        """AbstractStorage.list should have the correct signature."""
        from flywheel.storage import AbstractStorage
        import inspect

        sig = inspect.signature(AbstractStorage.list)
        params = list(sig.parameters.keys())

        assert 'self' in params
        # status should be optional
        assert 'status' in params

    def test_get_method_signature(self):
        """AbstractStorage.get should have the correct signature."""
        from flywheel.storage import AbstractStorage
        import inspect

        sig = inspect.signature(AbstractStorage.get)
        params = list(sig.parameters.keys())

        assert 'self' in params
        assert 'todo_id' in params

    def test_update_method_signature(self):
        """AbstractStorage.update should have the correct signature."""
        from flywheel.storage import AbstractStorage
        import inspect

        sig = inspect.signature(AbstractStorage.update)
        params = list(sig.parameters.keys())

        assert 'self' in params
        assert 'todo' in params

    def test_delete_method_signature(self):
        """AbstractStorage.delete should have the correct signature."""
        from flywheel.storage import AbstractStorage
        import inspect

        sig = inspect.signature(AbstractStorage.delete)
        params = list(sig.parameters.keys())

        assert 'self' in params
        assert 'todo_id' in params

    def test_get_next_id_method_signature(self):
        """AbstractStorage.get_next_id should have the correct signature."""
        from flywheel.storage import AbstractStorage
        import inspect

        sig = inspect.signature(AbstractStorage.get_next_id)
        params = list(sig.parameters.keys())

        assert 'self' in params
