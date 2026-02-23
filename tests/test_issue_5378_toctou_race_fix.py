"""Regression test for issue #5378: TOCTOU race condition in _ensure_parent_directory.

This test verifies that concurrent calls to save() on the same new path
do not raise OSError/FileExistsError when the directory is created by
another concurrent process.
"""

import concurrent.futures
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTOCTOURaceFix:
    """Test TOCTOU race condition fix in _ensure_parent_directory."""

    def test_concurrent_save_to_new_path_no_race_error(self, tmp_path: Path) -> None:
        """Verify concurrent saves to a new path don't raise FileExistsError."""
        # Use a non-existent subdirectory to trigger mkdir
        db_path = tmp_path / "new_subdir" / "db.json"
        todos = [Todo(id=1, text="Test todo", done=False)]
        errors = []
        successes = 0

        def save_todos() -> None:
            nonlocal successes
            storage = TodoStorage(str(db_path))
            storage.save(todos)
            successes += 1

        # Run 10 concurrent saves to trigger potential race
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(save_todos) for _ in range(10)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except (OSError, FileExistsError) as e:
                    errors.append(e)

        # No race condition errors should occur
        assert len(errors) == 0, f"Got {len(errors)} race condition errors: {errors}"
        # At least some saves should succeed
        assert successes >= 1, "At least one save should succeed"

    def test_ensure_parent_directory_with_exist_ok(self, tmp_path: Path) -> None:
        """Verify _ensure_parent_directory handles concurrent directory creation."""
        from flywheel.storage import _ensure_parent_directory

        db_path = tmp_path / "concurrent_dir" / "db.json"

        def ensure_dir() -> None:
            _ensure_parent_directory(db_path)

        # Run concurrent ensure_parent_directory calls
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(ensure_dir) for _ in range(10)]
            for future in concurrent.futures.as_completed(futures):
                # Should not raise FileExistsError
                future.result()

        # Directory should exist
        assert db_path.parent.is_dir()

    def test_file_as_parent_still_raises_valueerror(self, tmp_path: Path) -> None:
        """Verify file-as-directory still raises ValueError after fix."""
        # Create a file where a directory would be expected
        file_path = tmp_path / "regular_file.txt"
        file_path.write_text("I am a file")

        # Try to use a path that would require the file to be a directory
        db_path = file_path / "subdir" / "db.json"

        storage = TodoStorage(str(db_path))
        with pytest.raises(ValueError, match="exists as a file, not a directory"):
            storage.save([Todo(id=1, text="Test", done=False)])
