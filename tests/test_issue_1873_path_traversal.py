"""Regression test for issue #1873: Path traversal via path parameter.

This test suite verifies that TodoStorage properly validates paths
to prevent directory traversal attacks via '../' sequences.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestPathTraversalPrevention:
    """Tests for path traversal vulnerability prevention."""

    def test_path_with_parent_directory_traversal_raises_error(self, tmp_path: Path) -> None:
        """Test that paths with '../' sequences are rejected."""
        # Change to tmp_path for testing
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # Attempt to create a storage with path traversal
            malicious_path = "../../../etc/passwd"

            with pytest.raises(ValueError, match=r"path traversal|'../'"):
                storage = TodoStorage(malicious_path)
                # Try to use the storage to trigger validation
                storage.save([Todo(id=1, text="test")])
        finally:
            os.chdir(original_cwd)

    def test_safe_relative_path_works_normally(self, tmp_path: Path) -> None:
        """Test that safe relative paths work normally."""
        # Change to tmp_path for relative path testing
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            storage = TodoStorage("safe.json")
            todos = [Todo(id=1, text="test")]
            storage.save(todos)

            # Verify file was created and data can be loaded
            loaded = storage.load()
            assert len(loaded) == 1
            assert loaded[0].text == "test"
        finally:
            os.chdir(original_cwd)

    def test_nested_safe_path_works_normally(self, tmp_path: Path) -> None:
        """Test that safe nested paths work normally."""
        # Change to tmp_path for testing
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            nested_path = "subdir/safe.json"
            storage = TodoStorage(nested_path)
            todos = [Todo(id=1, text="nested test")]
            storage.save(todos)

            # Verify file was created and data can be loaded
            loaded = storage.load()
            assert len(loaded) == 1
            assert loaded[0].text == "nested test"
        finally:
            os.chdir(original_cwd)

    def test_path_traversal_with_double_dots_in_middle(self, tmp_path: Path) -> None:
        """Test that '../' in the middle of the path is also rejected."""
        # Change to tmp_path for testing
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # Create a subdir first
            Path("subdir").mkdir(exist_ok=True)

            malicious_path = "subdir/../../../etc/passwd"

            with pytest.raises(ValueError, match=r"path traversal|'../'"):
                storage = TodoStorage(malicious_path)
                storage.save([Todo(id=1, text="test")])
        finally:
            os.chdir(original_cwd)

    def test_initialization_rejects_traversal_on_construction(self, tmp_path: Path) -> None:
        """Test that path validation happens at construction time."""
        # Change to tmp_path for testing
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            malicious_path = "../../../etc/passwd"

            # Validation should happen at construction
            with pytest.raises(ValueError, match=r"path traversal|'../'"):
                TodoStorage(malicious_path)
        finally:
            os.chdir(original_cwd)

    def test_path_within_allowed_directory_works(self, tmp_path: Path) -> None:
        """Test that paths within the allowed working directory work."""
        # Change to tmp_path for testing
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # A path within tmp_path should work
            safe_path = "data/todos.json"
            storage = TodoStorage(safe_path)
            todos = [Todo(id=1, text="safe todo")]
            storage.save(todos)

            loaded = storage.load()
            assert len(loaded) == 1
            assert loaded[0].text == "safe todo"
        finally:
            os.chdir(original_cwd)

    def test_absolute_path_works(self, tmp_path: Path) -> None:
        """Test that absolute paths work normally (they don't contain '..')."""
        # Absolute paths are allowed - they point to a specific location
        safe_absolute_path = tmp_path / "data" / "todos.json"
        storage = TodoStorage(str(safe_absolute_path))
        todos = [Todo(id=1, text="safe absolute path todo")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "safe absolute path todo"

    def test_backslash_traversal_on_windows_style_path(self, tmp_path: Path) -> None:
        """Test that backslash-based traversal is also rejected."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # Windows-style path traversal
            malicious_path = "..\\..\\etc\\passwd"

            with pytest.raises(ValueError, match=r"path traversal|'../'"):
                TodoStorage(malicious_path)
        finally:
            os.chdir(original_cwd)
