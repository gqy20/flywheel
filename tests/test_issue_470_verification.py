"""Test to verify _secure_all_parent_directories method exists and works.

This test verifies Issue #470: The method _secure_all_parent_directories
should be implemented in the Storage class.
"""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from flywheel.storage import Storage


class TestSecureAllParentDirectoriesExists:
    """Test that _secure_all_parent_directories method exists."""

    def test_method_exists(self):
        """Test that _secure_all_parent_directories method is defined."""
        # Check that the method exists
        assert hasattr(Storage, '_secure_all_parent_directories'), \
            "_secure_all_parent_directories method should exist in Storage class"

    def test_method_is_callable(self):
        """Test that _secure_all_parent_directories is callable."""
        assert callable(getattr(Storage, '_secure_all_parent_directories')), \
            "_secure_all_parent_directories should be a callable method"

    def test_method_called_during_init(self):
        """Test that _secure_all_parent_directories is called during __init__."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test" / "todos.json"

            # Mock _secure_all_parent_directories to track if it's called
            with mock.patch.object(
                Storage,
                '_secure_all_parent_directories',
                wraps=Storage._secure_all_parent_directories
            ) as mock_secure:
                storage = Storage(path=str(test_path))

                # Verify that _secure_all_parent_directories was called
                mock_secure.assert_called_once()
                call_args = mock_secure.call_args

                # Verify it was called with the parent directory
                expected_parent = test_path.parent
                actual_parent = call_args[0][0] if call_args[0] else None

                assert actual_parent == expected_parent, \
                    f"_secure_all_parent_directories should be called with {expected_parent}, got {actual_parent}"

    def test_method_secures_parent_directories(self):
        """Test that _secure_all_parent_directories actually secures all parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a nested path structure
            test_path = Path(tmpdir) / "level1" / "level2" / "todos.json"

            # Track which directories are secured
            secured_dirs = []

            original_secure_directory = Storage._secure_directory

            def mock_secure_directory(self, directory):
                secured_dirs.append(directory)
                # Call original to actually create the directories
                return original_secure_directory(self, directory)

            with mock.patch.object(
                Storage,
                '_secure_directory',
                mock_secure_directory
            ):
                storage = Storage(path=str(test_path))

            # Verify that parent directories were secured
            # The method should secure all parent directories that exist
            expected_parents = [
                test_path.parent.parent,  # level1
                test_path.parent,          # level2
            ]

            # Filter to only directories that actually exist
            expected_existing = [p for p in expected_parents if p.exists()]

            # Note: _secure_all_parent_directories secures all existing parents
            # from the target directory up to (but not including) the root
            actual_secured = [d for d in secured_dirs if d in expected_existing]

            # At minimum, the immediate parent should be secured
            assert test_path.parent in secured_dirs, \
                f"Immediate parent {test_path.parent} should be secured"

    def test_method_signature(self):
        """Test that _secure_all_parent_directories has the correct signature."""
        import inspect

        method = getattr(Storage, '_secure_all_parent_directories')

        # Get method signature
        sig = inspect.signature(method)

        # Should have 'self' and 'directory' parameters
        params = list(sig.parameters.keys())
        assert 'directory' in params, \
            "_secure_all_parent_directories should have 'directory' parameter"

    def test_method_has_docstring(self):
        """Test that _secure_all_parent_directories has documentation."""
        method = getattr(Storage, '_secure_all_parent_directories')

        assert method.__doc__ is not None, \
            "_secure_all_parent_directories should have a docstring"

        # Verify docstring mentions key security concepts
        doc = method.__doc__.lower()
        assert any(keyword in doc for keyword in ['secure', 'permission', 'parent']), \
            "Docstring should mention security-related terms"


class TestSecureAllParentDirectoriesFunctionality:
    """Test the functionality of _secure_all_parent_directories."""

    def test_secures_all_parents_on_unix(self):
        """Test that all parent directories are secured on Unix."""
        if os.name == 'nt':  # Windows
            pytest.skip("This test is for Unix systems only")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a deeply nested path
            test_path = Path(tmpdir) / "a" / "b" / "c" / "todos.json"

            storage = Storage(path=str(test_path))

            # Verify all parent directories have correct permissions
            current = test_path.parent
            while current != Path(tmpdir) and current.exists():
                stat_info = current.stat()
                mode = stat_info.st_mode & 0o777
                assert mode == 0o700, \
                    f"Directory {current} should have 0o700 permissions, got {oct(mode)}"
                current = current.parent

    def test_no_error_on_existing_directories(self):
        """Test that method doesn't error when directories already exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Pre-create the directory structure
            test_path = Path(tmpdir) / "existing" / "todos.json"
            test_path.parent.mkdir(parents=True, exist_ok=True)

            # This should not raise an error
            storage = Storage(path=str(test_path))

            assert storage is not None
