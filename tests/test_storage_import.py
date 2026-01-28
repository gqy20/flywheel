"""
Test for Issue #1010: Verify storage.py can be imported and used.

This test ensures that the storage.py file is complete and has no
truncated code or syntax errors that would prevent it from being imported.
"""

import pytest


def test_storage_module_can_be_imported():
    """Test that storage module can be imported without errors."""
    # This test will fail if the file has syntax errors or is truncated
    try:
        from flywheel import storage
        assert storage is not None
    except (SyntaxError, ImportError) as e:
        pytest.fail(f"Failed to import storage module: {e}")


def test_storage_filestorage_class_exists():
    """Test that FileStorage class exists and is accessible."""
    from flywheel.storage import FileStorage
    assert FileStorage is not None
    assert hasattr(FileStorage, '__name__')
    assert FileStorage.__name__ == 'FileStorage'


def test_storage_degraded_mode_function_exists():
    """Test that _is_degraded_mode function exists."""
    from flywheel.storage import _is_degraded_mode
    assert _is_degraded_mode is not None
    assert callable(_is_degraded_mode)


def test_windows_import_handling():
    """Test that Windows import section is properly formatted.

    This test verifies that the section around line 238-310
    (Windows import handling) is complete and properly structured.
    """
    import ast
    import os

    # Read and parse the storage.py file
    storage_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'src',
        'flywheel',
        'storage.py'
    )

    with open(storage_path, 'r') as f:
        source = f.read()

    # Verify the file can be parsed as valid Python
    try:
        tree = ast.parse(source)
        assert tree is not None
    except SyntaxError as e:
        pytest.fail(
            f"storage.py has syntax errors (possibly truncated): {e}"
        )

    # Verify the file contains expected sections
    assert 'if os.name ==' in source or 'os.name' in source
    assert 'win32' in source or 'fcntl' in source
