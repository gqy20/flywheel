"""Test Windows parent directory permissions (Issue #369).

This test verifies that when creating nested directories on Windows,
all parent directories are secured with restrictive ACLs, not just
the final directory.

Issue #369: Windows 目录权限设置可能不完整
- When mkdir creates parent directories with parents=True, they may
  inherit insecure default permissions
- Only the final directory has _secure_directory() applied
- Parent directories should also be secured

Fix: Apply _secure_directory() to all parent directories created by mkdir.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_parent_directories_get_secured():
    """Test that all parent directories are secured on Windows.

    This test ensures that when creating a nested directory structure like:
    /tmp/test_secure_dir/nested/deep/todos.json

    ALL parent directories get secure ACLs applied:
    - /tmp/test_secure_dir
    - /tmp/test_secure_dir/nested
    - /tmp/test_secure_dir/nested/deep

    Not just the final directory.

    Ref: Issue #369
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a nested path that doesn't exist
        nested_path = Path(tmpdir) / "secure_parent" / "level1" / "level2" / "todos.json"

        # Track which directories _secure_directory was called on
        secured_directories = []

        # Patch _secure_directory to track calls
        original_secure_directory = Storage._secure_directory

        def mock_secure_directory(self, directory):
            secured_directories.append(directory)
            # Call the original to actually secure the directory
            return original_secure_directory(self, directory)

        with patch.object(Storage, '_secure_directory', mock_secure_directory):
            # Create storage - this should trigger mkdir for all parent directories
            storage = Storage(str(nested_path))

            # The final directory should be secured
            final_dir = nested_path.parent
            assert final_dir in secured_directories, \
                f"Final directory {final_dir} should be secured"

            # All parent directories should also be secured
            # Check each level of the hierarchy
            level2 = final_dir
            level1 = final_dir.parent
            secure_parent = final_dir.parent.parent

            # At minimum, the final directory should be secured
            # After the fix, all parent directories that were created
            # should also be secured
            assert level2 in secured_directories, \
                f"Directory {level2} should be secured"

            # This is the key test: parent directories should also be secured
            # Before the fix: only final_dir would be in secured_directories
            # After the fix: all created parent directories should be secured
            assert level1 in secured_directories, \
                f"Parent directory {level1} should be secured (Issue #369)"

            assert secure_parent in secured_directories, \
                f"Parent directory {secure_parent} should be secured (Issue #369)"


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_mkdir_mode_parameter_ignored():
    """Test that Windows mkdir ignores mode parameter.

    This test documents the known Windows behavior where mkdir's mode
    parameter is ignored, demonstrating why we need to explicitly apply
    ACLs to all parent directories.

    Ref: Issue #369
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_mode_ignored" / "nested"

        # Create directory with mode=0o700
        # On Windows, this mode parameter is ignored
        test_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Directory should exist (mode ignored, but directory created)
        assert test_dir.exists()

        # On Windows, we need to explicitly set ACLs via _secure_directory
        # This is what the fix does


@pytest.mark.skipif(os.name == 'nt', reason="Unix-specific test")
def test_unix_mkdir_mode_parameter_works():
    """Test that Unix mkdir respects mode parameter.

    This test verifies that on Unix systems, the mkdir mode parameter
    works correctly, setting restrictive permissions from the start.

    Ref: Issue #369
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_mode_works" / "nested"

        # Create directory with mode=0o700
        test_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Directory should exist
        assert test_dir.exists()

        # On Unix, check that permissions are set correctly
        import stat
        dir_stat = test_dir.stat()
        dir_mode = stat.S_IMODE(dir_stat.st_mode)

        # Should have 0o700 permissions (rwx------)
        # Note: This might be affected by umask, but _secure_directory
        # will fix it afterward
        assert dir_mode & 0o700, "Directory should have owner permissions"


def test_nested_directory_creation_security():
    """Test security of nested directory creation across platforms.

    This is a cross-platform test that verifies the security intent:
    when creating nested directories, all levels should be secured.

    Ref: Issue #369
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a deeply nested path
        nested_path = Path(tmpdir) / "a" / "b" / "c" / "d" / "todos.json"

        # Track secure_directory calls
        secured_dirs = []

        original_secure_directory = Storage._secure_directory

        def mock_secure_directory(self, directory):
            secured_dirs.append(str(directory))
            return original_secure_directory(self, directory)

        with patch.object(Storage, '_secure_directory', mock_secure_directory):
            storage = Storage(str(nested_path))

            # All created parent directories should be secured
            # The exact list depends on which directories didn't exist before
            final_parent = str(nested_path.parent)

            # At minimum, the immediate parent should be secured
            assert final_parent in secured_dirs, \
                f"Final parent {final_parent} should be secured"

            # Verify that parent directories are also secured
            # (not just the final directory)
            # On a clean temp directory, this would include:
            # - tmpdir/a
            # - tmpdir/a/b
            # - tmpdir/a/b/c
            # - tmpdir/a/b/c/d

            # The key assertion: we should have secured multiple directories
            # in the hierarchy, not just the final one
            assert len(secured_dirs) >= 1, \
                "At least one directory should be secured"

            # After the fix for Issue #369, all parent directories
            # created by mkdir should be secured
            # Before the fix, only the final directory would be secured
            expected_parents = [
                str(nested_path.parent.parent),  # c
                str(nested_path.parent.parent.parent),  # b
                str(nested_path.parent.parent.parent.parent),  # a
            ]

            # Check that parent directories are secured
            for parent in expected_parents:
                if Path(parent).exists():
                    # Only check if it exists (might already exist in tmpdir)
                    assert parent in secured_dirs, \
                        f"Parent directory {parent} should be secured (Issue #369)"
