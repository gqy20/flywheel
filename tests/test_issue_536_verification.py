"""
Verification test for Issue #536 - False Positive

Issue #536 reported that `_secure_all_parent_directories` method was undefined
when called at line 111 in storage.py. This test verifies that the method exists
and is callable, confirming this was a false positive from the AI scanner.

The method is actually defined at line 1219 in the same file.
"""

import inspect
import tempfile
from pathlib import Path

from flywheel import TodoStorage


def test_secure_all_parent_directories_method_exists():
    """Verify that _secure_all_parent_directories method exists and is callable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test.todo"
        storage = TodoStorage(storage_path)

        # Verify the method exists
        assert hasattr(storage, '_secure_all_parent_directories'), \
            "TodoStorage should have _secure_all_parent_directories method"

        # Verify it's a method (callable)
        assert callable(storage._secure_all_parent_directories), \
            "_secure_all_parent_directories should be callable"

        # Verify the method signature
        method = getattr(storage, '_secure_all_parent_directories')
        sig = inspect.signature(method)

        # Should accept 'directory' parameter
        params = list(sig.parameters.keys())
        assert 'directory' in params, \
            f"_secure_all_parent_directories should have 'directory' parameter, got: {params}"


def test_secure_all_parent_directories_callable():
    """Verify that _secure_all_parent_directories can be called without errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "subdir" / "test.todo"
        storage = TodoStorage(storage_path)

        # The method is called during __init__ at line 111
        # If we get here without exception, the method exists and works
        assert storage is not None
        assert storage.path == storage_path

        # Verify parent directory was created and secured
        assert storage_path.parent.exists(), \
            "Parent directory should be created during TodoStorage initialization"


def test_secure_all_parent_directories_direct_call():
    """Verify direct call to _secure_all_parent_directories works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test.todo"
        storage = TodoStorage(storage_path)

        test_dir = Path(tmpdir) / "test_secure_dir"

        # Direct call should work without errors
        storage._secure_all_parent_directories(test_dir)

        # Verify directory was created
        assert test_dir.exists(), \
            "Directory should be created by _secure_all_parent_directories"
