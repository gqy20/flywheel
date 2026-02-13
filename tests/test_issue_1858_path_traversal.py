"""Regression tests for issue #1858: Path traversal vulnerability.

This test suite verifies that the path parameter to TodoStorage is validated
to prevent path traversal attacks via '..' components that could escape the
intended directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestPathTraversalValidation:
    """Tests for path traversal vulnerability prevention."""

    def test_path_traversal_with_double_dots_is_rejected(self, tmp_path: Path) -> None:
        """Test that paths containing '..' components that escape cwd are rejected."""
        # Change to tmp_path to have a controlled working directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Attempt to create storage with a path traversal attack
            # This path would try to access /etc/passwd on Unix systems
            traversal_path = "../../../etc/passwd"

            with pytest.raises(ValueError, match=r"[Pp]ath.*traversal|escape|valid"):
                TodoStorage(traversal_path)

        finally:
            os.chdir(original_cwd)

    def test_path_with_backtracking_is_normalized_and_warns(self, tmp_path: Path) -> None:
        """Test that paths with '..' are normalized and a warning is issued."""
        import os
        import warnings

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create a subdirectory for testing
            subdir = tmp_path / "subdir"
            subdir.mkdir()

            # Path that uses '..' but resolves within the safe directory
            # Should be allowed with a warning
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                storage = TodoStorage("subdir/../test.json")

                # The path should be normalized
                # A warning should be issued for paths containing '..'
                assert len(w) == 1
                assert "normalized" in str(w[0].message).lower()

            # Verify the path is normalized (no '..' in final path)
            assert ".." not in str(storage.path)

        finally:
            os.chdir(original_cwd)

    def test_absolute_path_is_allowed(self, tmp_path: Path) -> None:
        """Test that absolute paths are allowed (user explicitly chose location)."""
        db_path = tmp_path / "absolute.json"

        storage = TodoStorage(str(db_path))
        storage.save([Todo(id=1, text="test")])

        assert db_path.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

    def test_relative_path_within_cwd_is_allowed(self, tmp_path: Path) -> None:
        """Test that relative paths staying within cwd work correctly."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create subdirectory
            subdir = tmp_path / "data"
            subdir.mkdir()

            # Path within current working directory
            storage = TodoStorage("data/todos.json")
            storage.save([Todo(id=1, text="relative")])

            assert (tmp_path / "data" / "todos.json").exists()

        finally:
            os.chdir(original_cwd)

    def test_path_escaping_cwd_rejected_with_clear_message(self, tmp_path: Path) -> None:
        """Test that paths escaping the current working directory are rejected with a clear error."""
        import os

        original_cwd = os.getcwd()
        try:
            # Create a subdirectory and change into it
            inner_dir = tmp_path / "inner"
            inner_dir.mkdir()
            os.chdir(inner_dir)

            # Try to escape to parent directory's sibling
            traversal_path = "../other_dir/db.json"

            with pytest.raises(ValueError, match=r"[Pp]ath"):
                TodoStorage(traversal_path)

        finally:
            os.chdir(original_cwd)

    def test_absolute_system_path_is_allowed_but_wont_write(self, tmp_path: Path) -> None:
        """Test that absolute paths to system files don't raise path traversal errors.

        Note: While the path is accepted by the validation, actual file operations
        may still fail due to OS permissions. The fix focuses on preventing
        relative path traversal attacks, not blocking all file system access.
        """
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # This should NOT raise a path traversal error (it's an absolute path)
            # The user explicitly chose an absolute path
            storage = TodoStorage("/etc/passwd")

            # The path is resolved (absolute paths are allowed)
            assert storage.path.is_absolute()

        finally:
            os.chdir(original_cwd)
