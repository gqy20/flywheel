"""Regression tests for issue #3907: TOCTOU race condition in _ensure_parent_directory.

Issue: The _ensure_parent_directory function has a Time-of-Check-Time-of-Use race
condition. Between checking if parent paths are files (line 35-40) and creating
the directory (line 43-50), a malicious process could create a conflicting file.

The fix should:
1. Use mkdir with exist_ok=True and handle FileExistsError
2. Provide clear error messages distinguishing 'path is file' vs 'directory exists'

These tests verify the race condition is handled correctly.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory


class TestTOCTOURaceCondition:
    """Test that TOCTOU race conditions are handled properly."""

    def test_ensure_parent_directory_detects_file_conflict_on_mkdir(self, tmp_path: Path) -> None:
        """Issue #3907: File created between check and mkdir should be detected.

        Simulates the scenario where:
        1. _ensure_parent_directory checks that parent doesn't exist
        2. Attacker creates a file at that path (race condition window)
        3. mkdir fails because file exists

        The fix should handle FileExistsError and provide a clear error message.
        """
        parent_dir = tmp_path / "target"
        db_path = parent_dir / "todo.json"

        original_mkdir = Path.mkdir

        def patched_mkdir(self: Path, *args, **kwargs) -> None:
            # Before the actual mkdir, create a file at the target path
            if str(self) == str(parent_dir):
                # Simulate attacker creating file right before mkdir
                parent_dir.write_text("attacker file")
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", patched_mkdir):
            # Should raise ValueError with clear message about file conflict
            with pytest.raises(ValueError, match=r"(file|not a directory)"):
                _ensure_parent_directory(db_path)

    def test_ensure_parent_directory_raises_on_mkdir_file_exists_error(self, tmp_path: Path) -> None:
        """Issue #3907: Verify FileExistsError from mkdir is converted to ValueError.

        When mkdir raises FileExistsError because a file exists (not a directory),
        the function should convert this to a clear ValueError.
        """
        parent_dir = tmp_path / "target"
        db_path = parent_dir / "todo.json"

        original_mkdir = Path.mkdir

        def patched_mkdir(self: Path, *args, **kwargs) -> None:
            # Simulate FileExistsError when trying to create directory
            if str(self) == str(parent_dir):
                raise FileExistsError(f"[Errno 17] File exists: '{self}'")
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", patched_mkdir):
            # Should raise ValueError with clear message
            with pytest.raises(ValueError, match=r"(file|not a directory|exists)"):
                _ensure_parent_directory(db_path)

    def test_clear_error_when_path_component_is_file(self, tmp_path: Path) -> None:
        """Issue #3907: Static case - error message should be clear about file conflict.

        When a path component exists as a file (not race condition), the error
        should clearly indicate the problem.
        """
        # Create a file where we need a directory
        blocking_file = tmp_path / "blocking.json"
        blocking_file.write_text("I am a file")

        # Try to use a path that requires blocking.json to be a directory
        db_path = blocking_file / "data" / "todo.json"

        storage = TodoStorage(str(db_path))
        with pytest.raises(ValueError, match=r"(file|not a directory)"):
            storage.save([])

    def test_mkdir_with_exist_ok_handles_directory_exists(self, tmp_path: Path) -> None:
        """Issue #3907: exist_ok=True should handle case where directory is created concurrently.

        If another process legitimately creates the directory at the same time,
        the operation should succeed (not raise an error).
        """
        parent_dir = tmp_path / "shared"
        db_path = parent_dir / "todo.json"

        original_mkdir = Path.mkdir

        mkdir_call_count = 0

        def patched_mkdir(self: Path, *args, **kwargs) -> None:
            nonlocal mkdir_call_count
            # Simulate another process creating the directory first
            if str(self) == str(parent_dir):
                mkdir_call_count += 1
                if mkdir_call_count == 1:
                    os.makedirs(str(parent_dir), exist_ok=True)
            try:
                return original_mkdir(self, *args, **kwargs)
            except FileExistsError:
                # If it's a directory, this should be fine with exist_ok=True
                if self.is_dir():
                    return
                raise

        with patch.object(Path, "mkdir", patched_mkdir):
            _ensure_parent_directory(db_path)
            # Should succeed since another process created the directory
            assert parent_dir.is_dir()
