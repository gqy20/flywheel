"""Tests for issue #2195: _ensure_parent_directory() comment accuracy.

The issue is about a misleading comment that overstates the safety guarantees
of exist_ok=False. The validation only prevents file-as-directory confusion,
but does not protect against TOCTOU race conditions where another process
creates the directory concurrently.
"""

import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import _ensure_parent_directory


class TestEnsureParentDirectoryCommentAccuracy:
    """Tests verifying that _ensure_parent_directory behaves reasonably.

    The misleading comment claimed exist_ok=False was "safe since we validated above",
    but validation only checks for file-as-directory issues, not concurrent directory
    creation. These tests document the actual behavior.
    """

    def test_handles_existing_directory_gracefully(self, tmp_path):
        """Test that existing directories are handled without error.

        The current implementation uses exist_ok=False, which would raise
        FileExistsError if a directory is created between the exists() check
        and the mkdir() call (TOCTOU race). This test documents that in the
        normal single-threaded case, the function works.
        """
        # Pre-create the parent directory
        parent = tmp_path / "existing_dir"
        parent.mkdir(parents=True)

        # Call _ensure_parent_directory with a file path whose parent exists
        file_path = parent / "db.json"
        # Should not raise an error since parent already exists
        _ensure_parent_directory(file_path)

        # Verify parent still exists and is a directory
        assert parent.is_dir()

    def test_creates_missing_parent_directory(self, tmp_path):
        """Test that missing parent directories are created."""
        # Path with non-existent parent
        parent = tmp_path / "new_dir" / "subdir"
        file_path = parent / "db.json"

        # Parent shouldn't exist yet
        assert not parent.exists()

        # Call _ensure_parent_directory
        _ensure_parent_directory(file_path)

        # Verify parent was created
        assert parent.is_dir()

    def test_raises_value_error_when_parent_is_file(self, tmp_path):
        """Test that ValueError is raised when a parent component is a file.

        This is the primary validation that the comment refers to - checking
        for file-as-directory confusion.
        """
        # Create a file where we need a directory
        file_as_dir = tmp_path / "file.json"
        file_as_dir.write_text("{}")

        # Try to use a path that requires this file to be a directory
        file_path = file_as_dir / "subdir" / "db.json"

        # Should raise ValueError
        with pytest.raises(ValueError, match="exists as a file, not a directory"):
            _ensure_parent_directory(file_path)

    def test_deeply_nested_path_with_file_in_middle(self, tmp_path):
        """Test validation of deeply nested paths with a file in the middle."""
        # Create directory structure
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()

        # Create a file blocking the path
        blocking_file = tmp_path / "level1" / "level2" / "blocking.json"
        blocking_file.write_text("{}")

        # Try to create path that requires going through the file
        file_path = tmp_path / "level1" / "level2" / "blocking.json" / "deep" / "db.json"

        # Should raise ValueError
        with pytest.raises(ValueError, match="exists as a file, not a directory"):
            _ensure_parent_directory(file_path)

    def test_comment_accuracy_documentation(self, tmp_path):
        """Documentation test for the comment accuracy issue.

        This test exists to document the issue: the comment at line 45 of
        storage.py claims exist_ok=False is safe "since we validated above",
        but the validation only checks for file-as-directory confusion.
        It does not protect against TOCTOU race conditions where another
        process creates the directory between exists() and mkdir().

        The fix is to either:
        1. Use exist_ok=True (simpler and more robust)
        2. Update the comment to accurately reflect the actual safety guarantees

        This test passes because the current behavior is acceptable,
        but the comment is misleading about the safety guarantees.
        """
        # The actual behavior is reasonable - this test documents it
        parent = tmp_path / "doc_test"
        file_path = parent / "db.json"

        # First call creates the directory
        _ensure_parent_directory(file_path)
        assert parent.is_dir()

        # Second call with same path should also work
        # (because parent.exists() returns True, so mkdir is skipped)
        _ensure_parent_directory(file_path)

    def test_concurrent_directory_creation_theoretical(self, tmp_path):
        """Theoretical test for TOCTOU race condition.

        This test documents the theoretical race condition that the
        misleading comment fails to acknowledge. In production with
        multiple processes, a race could occur between exists() and mkdir().

        Note: This is difficult to test deterministically without
        synchronization primitives, so we document the behavior here.
        """
        parent = tmp_path / "race_test"
        file_path = parent / "db.json"

        # In a concurrent scenario, if another process creates 'parent'
        # between our exists() check and our mkdir() call, we would get
        # FileExistsError with exist_ok=False.
        #
        # The current code checks `if not parent.exists()` before mkdir,
        # so in normal usage we skip mkdir if the directory already exists.
        # But the TOCTOU window still exists.

        # Current behavior: single-threaded, this works fine
        _ensure_parent_directory(file_path)

        # Calling again also works because of the exists() check
        _ensure_parent_directory(file_path)

        # The comment should acknowledge that:
        # - exist_ok=False will raise if directory is created concurrently
        # - The exists() check mitigates but doesn't eliminate the TOCTOU risk
        # - This is intentional to surface potential race conditions
