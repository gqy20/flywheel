"""Tests for path traversal vulnerability fix (issue #1873).

This test suite verifies that TodoStorage properly validates paths
to prevent directory traversal attacks via '../' sequences.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestPathTraversalPrevention:
    """Tests for path traversal vulnerability prevention."""

    def test_relative_path_traversal_with_double_dot_rejected(self, tmp_path: Path) -> None:
        """Test that paths with '../' sequences that escape cwd are rejected.

        This prevents attackers from escaping the intended directory
        and accessing or modifying files outside the working directory.
        """
        # Change to tmp_path as base directory
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Attempt to use path traversal to escape tmp_path
            malicious_path = "../../../etc/passwd"
            with pytest.raises(ValueError, match=r"[Pp]ath.*traversal"):
                storage = TodoStorage(malicious_path)
                storage.save([Todo(id=1, text="malicious")])
        finally:
            os.chdir(original_cwd)

    def test_complex_path_traversal_rejected(self, tmp_path: Path) -> None:
        """Test that complex '../' traversal patterns are rejected."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Various traversal patterns that escape cwd
            malicious_paths = [
                "../../../etc/passwd",
                "./../../../etc/passwd",
                "../outside.json",
                "../../outside.json",
            ]
            for path in malicious_paths:
                with pytest.raises(ValueError, match=r"[Pp]ath.*traversal"):
                    storage = TodoStorage(path)
                    storage.save([Todo(id=1, text="test")])
        finally:
            os.chdir(original_cwd)

    def test_path_traversal_that_stays_within_cwd_allowed(self, tmp_path: Path) -> None:
        """Test that '../' that stays within cwd is allowed (e.g., subdir/../file)."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Create a subdirectory
            subdir = tmp_path / "subdir"
            subdir.mkdir()

            # This path contains '..' but resolves to within cwd
            safe_path = "subdir/../safe.json"
            storage = TodoStorage(safe_path)
            storage.save([Todo(id=1, text="test")])
            loaded = storage.load()
            assert len(loaded) == 1
            assert loaded[0].text == "test"
        finally:
            os.chdir(original_cwd)

    def test_safe_relative_path_works_normally(self, tmp_path: Path) -> None:
        """Test that safe relative paths work normally."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Safe paths should work fine
            safe_paths = [
                "safe.json",
                "subdir/safe.json",
                "./safe.json",
            ]
            for path in safe_paths:
                storage = TodoStorage(path)
                storage.save([Todo(id=1, text="test")])
                loaded = storage.load()
                assert len(loaded) == 1
                assert loaded[0].text == "test"
        finally:
            os.chdir(original_cwd)

    def test_path_with_dot_inside_directory_works(self, tmp_path: Path) -> None:
        """Test that paths with '.' inside a filename work (e.g., 'my.file.json')."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Paths with dots in filenames (but not '..' path segments)
            safe_path = "my.database.json"
            storage = TodoStorage(safe_path)
            storage.save([Todo(id=1, text="test")])
            loaded = storage.load()
            assert len(loaded) == 1
        finally:
            os.chdir(original_cwd)

    def test_absolute_path_allowed(self, tmp_path: Path) -> None:
        """Test that absolute paths are allowed (users may want to store DB anywhere)."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Absolute paths should be allowed - users may want to store
            # their database in a specific location (e.g., synced folder)
            safe_absolute_path = str(tmp_path / "safe.json")
            storage = TodoStorage(safe_absolute_path)
            storage.save([Todo(id=1, text="test")])
            loaded = storage.load()
            assert len(loaded) == 1
        finally:
            os.chdir(original_cwd)
