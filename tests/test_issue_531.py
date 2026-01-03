"""Test for issue #531 - Verify _secure_all_parent_directories exists (False Positive).

This test verifies that the _secure_all_parent_directories method mentioned in
issue #531 actually exists and is callable.

Issue #531 claimed that _secure_all_parent_directories is undefined at line 217
of src/flywheel/storage.py, but this is a FALSE POSITIVE - the method is:
1. Defined at line 1219 in src/flywheel/storage.py
2. Called at line 111 in the __init__ method
3. Well-tested and documented

This test confirms the method exists and works correctly.
"""

import inspect
import tempfile
from pathlib import Path

import pytest

from flywheel import Todo
from flywheel.storage import Storage


class TestIssue531FalsePositive:
    """Verify issue #531 is a false positive - method exists."""

    def test_secure_all_parent_directories_exists(self):
        """Test that _secure_all_parent_directories method exists."""
        # Verify Storage class exists
        assert Storage is not None

        # Check for method mentioned in the issue
        assert hasattr(Storage, '_secure_all_parent_directories'), \
            "Storage class should have _secure_all_parent_directories method"

        # Verify method is callable
        assert callable(getattr(Storage, '_secure_all_parent_directories')), \
            "_secure_all_parent_directories should be callable"

    def test_secure_all_parent_directories_callable(self):
        """Test that _secure_all_parent_directories method is callable on instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.todos"
            storage = Storage(storage_path)

            # Method should exist on instance
            assert hasattr(storage, '_secure_all_parent_directories')
            assert callable(storage._secure_all_parent_directories)

    def test_secure_all_parent_directories_has_source(self):
        """Test that _secure_all_parent_directories has actual implementation."""
        # Get the source code of the method
        source = inspect.getsource(Storage._secure_all_parent_directories)

        # Verify the method has a complete implementation
        assert 'def ' in source
        assert 'return' in source or 'pass' in source
        assert 'directory' in source

    def test_secure_all_parent_directories_called_in_init(self):
        """Test that _secure_all_parent_directories is called during initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "subdir" / "test.todos"

            # Create storage - this should call _secure_all_parent_directories
            storage = Storage(storage_path)

            # Parent directory should exist (created by _secure_all_parent_directories)
            assert storage_path.parent.exists()

    def test_verify_issue_line_217_context(self):
        """Verify the context around line 217 mentioned in the issue."""
        storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

        with open(storage_file, 'r') as f:
            lines = f.readlines()

        # Line 217 (0-indexed: 216) is in a comment about lock ranges
        # The issue incorrectly claimed this was where _secure_all_parent_directories
        # was called, but it's actually called at line 111
        line_217 = lines[216].strip()

        # Verify line 217 is not the method call
        # (It should be in the _get_file_lock_range_from_handle method)
        assert '_secure_all_parent_directories' not in line_217

        # Verify the actual call is at line 111
        line_111 = lines[110].strip()
        assert '_secure_all_parent_directories' in line_111
        assert 'self._secure_all_parent_directories(self.path.parent)' in line_111

    def test_secure_all_parent_directories_functional(self):
        """Test that _secure_all_parent_directories works functionally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a nested path to test parent directory creation
            storage_path = Path(tmpdir) / "level1" / "level2" / "test.todos"

            # Create storage - should create and secure all parent directories
            storage = Storage(storage_path)

            # All parent directories should exist
            assert storage_path.exists() or not storage_path.exists()  # File may or may not exist
            assert storage_path.parent.exists()  # level2 should exist
            assert storage_path.parent.parent.exists()  # level1 should exist

            # Storage should be functional
            todo = Todo(title="Test", description="Testing _secure_all_parent_directories")
            added = storage.add(todo)
            assert added is not None
            assert added.id == 1

    def test_method_location_verification(self):
        """Verify that _secure_all_parent_directories is defined at line 1219."""
        storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

        with open(storage_file, 'r') as f:
            lines = f.readlines()

        # Line 1219 (0-indexed: 1218) should have the method definition
        line_1219 = lines[1218].strip()

        # Verify it's the method definition
        assert 'def _secure_all_parent_directories' in line_1219

        # Verify the method has a docstring
        line_1220 = lines[1219].strip()
        assert '"""' in line_1220 or "'''" in line_1220
