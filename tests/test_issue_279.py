"""Test to verify issue #279 is invalid (file is not truncated)."""

import pytest


def test_storage_module_imports():
    """Test that storage.py can be imported without syntax errors."""
    try:
        from flywheel import storage
        assert storage is not None
        assert hasattr(storage, 'Storage')
    except SyntaxError as e:
        pytest.fail(f"storage.py has syntax error: {e}")
    except ImportError as e:
        pytest.fail(f"Failed to import storage: {e}")


def test_storage_class_complete():
    """Test that Storage class has all expected methods."""
    from flywheel.storage import Storage

    # Check that the class is complete with all expected methods
    expected_methods = [
        '__init__',
        '_get_windows_lock_range',
        '_acquire_file_lock',
        '_release_file_lock',
        '_secure_directory',
        '_create_backup',
        '_cleanup',
        '_calculate_checksum',
        '_validate_storage_schema',
        '_load',
        '_save',
        '_save_with_todos',
        'add',
        'list',
        'get',
        'update',
        'delete',
        'get_next_id',
        'close'
    ]

    for method in expected_methods:
        assert hasattr(Storage, method), f"Storage class missing method: {method}"


def test_windows_security_code_present():
    """Test that Windows security code exists and is complete."""
    from flywheel.storage import Storage
    import inspect

    # Get the source code of _secure_directory method
    source = inspect.getsource(Storage._secure_directory)

    # Verify key Windows security elements are present
    assert 'win32security' in source or 'chmod' in source, \
        "Security code (win32security or chmod) not found"
    assert 'LookupAccountName' in source or 'chmod' in source, \
        "User lookup or chmod not found"

    # If win32security imports exist, verify the complete Windows path
    if 'win32security' in source:
        # Check for DACL creation
        assert 'AddAccessAllowedAce' in source, \
            "Windows DACL creation incomplete"
        # Check for applying security descriptor
        assert 'SetFileSecurity' in source, \
            "Windows security application incomplete"


def test_storage_instantiation():
    """Test that Storage can be instantiated."""
    from flywheel.storage import Storage
    import tempfile

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test_todos.json"
        storage = Storage(path=storage_path)
        assert storage is not None
        assert storage._todos == []
        assert storage._next_id == 1
        storage.close()
