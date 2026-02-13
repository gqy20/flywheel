"""Tests for path traversal vulnerability (issue #1858).

This test suite verifies that user-supplied paths are validated
to prevent directory traversal attacks via '..' components.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestPathTraversalProtection:
    """Tests for preventing path traversal attacks."""

    def test_path_with_double_dot_is_rejected(self, tmp_path: Path) -> None:
        """Test that paths with '..' components that escape CWD are rejected."""
        # Create a subdirectory to escape from
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Attempt to escape via .. from the subdir
        escape_path = str(subdir / ".." / "escaped.json")

        with pytest.raises(ValueError, match="Path traversal|escape|outside|directory"):
            TodoStorage(escape_path)

    def test_deeply_nested_path_traversal_is_rejected(self, tmp_path: Path) -> None:
        """Test that deeply nested path traversal attempts are rejected."""
        subdir = tmp_path / "a" / "b" / "c"
        subdir.mkdir(parents=True)

        # Try to traverse up multiple levels: ../../../..
        escape_path = str(subdir / ".." / ".." / ".." / ".." / "escaped.json")

        with pytest.raises(ValueError, match="Path traversal|escape|outside|directory"):
            TodoStorage(escape_path)

    def test_valid_relative_path_within_directory_works(self, tmp_path: Path) -> None:
        """Test that legitimate relative paths within a directory work correctly."""
        # Valid path: subdir/file.json should work
        valid_path = str(tmp_path / "subdir" / "todos.json")

        # Should not raise
        storage = TodoStorage(valid_path)

        # Verify we can save and load
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

    def test_current_directory_relative_path_works(self, tmp_path: Path) -> None:
        """Test that paths relative to current directory work correctly."""
        # Valid path: ./todos.json should work
        valid_path = str(tmp_path / "todos.json")

        storage = TodoStorage(valid_path)

        todos = [Todo(id=1, text="another test")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "another test"

    def test_path_traversal_in_save_is_prevented(self, tmp_path: Path) -> None:
        """Test that path traversal during save operations is prevented."""
        # Create a storage with escaped path
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Try to create storage with traversal path
        escape_path = str(subdir / ".." / "escaped.json")

        # Should be rejected at construction time
        with pytest.raises(ValueError, match="Path traversal|escape|outside|directory"):
            storage = TodoStorage(escape_path)

    def test_simple_db_argument_with_path_traversal(self, tmp_path: Path) -> None:
        """Test the CLI --db parameter scenario described in the issue."""
        # Simulate: --db '../../../etc/passwd'
        # This would attempt to access system files via path traversal
        escape_path = "../../../etc/passwd"

        with pytest.raises(ValueError, match="Path traversal|escape|outside|directory"):
            TodoStorage(escape_path)

    def test_path_with_dotdot_in_middle_is_rejected(self, tmp_path: Path) -> None:
        """Test paths with '..' in the middle that escape CWD are rejected."""
        # Create a nested structure
        nested = tmp_path / "level1" / "level2"
        nested.mkdir(parents=True)

        # Path like: /tmp/xxx/level1/level2/../../escaped.json
        # This resolves to /tmp/xxx/escaped.json - outside CWD
        escape_path = str(nested / ".." / ".." / "escaped.json")

        with pytest.raises(ValueError, match="Path traversal|escape|outside|directory"):
            TodoStorage(escape_path)
