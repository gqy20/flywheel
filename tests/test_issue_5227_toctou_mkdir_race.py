"""Regression test for issue #5227: TOCTOU race in _ensure_parent_directory.

The _ensure_parent_directory function had a time-of-check-time-of-use (TOCTOU)
race condition where it checked if parent.exists() returned False, then called
mkdir with exist_ok=False. If another process created the directory between
the check and the mkdir, the operation would fail with FileExistsError.

The fix is to use exist_ok=True, making the operation idempotent.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


class TestTOCTOUMkdirRace:
    """Tests for TOCTOU race condition in _ensure_parent_directory."""

    def test_ensure_parent_directory_handles_concurrent_creation(self, tmp_path: Path) -> None:
        """Test that _ensure_parent_directory handles race where another
        process creates the directory between the exists() check and mkdir().

        This simulates a TOCTOU race condition by mocking Path.mkdir to
        raise FileExistsError on first call (simulating another process
        creating the directory concurrently).
        """
        test_file = tmp_path / "subdir" / "test.json"
        parent_dir = test_file.parent

        # Track mkdir calls
        mkdir_calls = []

        original_mkdir = Path.mkdir

        def mock_mkdir_race(self, parents: bool = False, exist_ok: bool = False):
            mkdir_calls.append((str(self), parents, exist_ok))

            # If this is the parent directory and exist_ok=False, simulate race
            if self == parent_dir and not exist_ok:
                # Simulate another process creating the directory
                original_mkdir(self, parents=parents, exist_ok=True)
                raise FileExistsError(
                    f"[Errno 17] File exists: '{self}' (simulated TOCTOU race)"
                )

            # Otherwise proceed normally
            return original_mkdir(self, parents=parents, exist_ok=True)

        with patch.object(Path, "mkdir", mock_mkdir_race):
            # This should NOT raise FileExistsError if the fix is applied
            # (i.e., exist_ok=True is used)
            _ensure_parent_directory(test_file)

        # Verify parent directory was created
        assert parent_dir.exists()
        assert parent_dir.is_dir()

    def test_save_succeeds_despite_concurrent_directory_creation(
        self, tmp_path: Path
    ) -> None:
        """Test that TodoStorage.save() succeeds even if another process
        creates the parent directory concurrently during _ensure_parent_directory.

        This is an end-to-end test that simulates the race condition scenario.
        """
        db = tmp_path / "subdir" / "todo.json"
        parent_dir = db.parent

        # Track mkdir calls to verify race handling
        mkdir_calls = []
        original_mkdir = Path.mkdir

        def mock_mkdir_race(self, parents: bool = False, exist_ok: bool = False):
            mkdir_calls.append((str(self), parents, exist_ok))

            # Simulate TOCTOU race: directory gets created by another process
            if self == parent_dir and not exist_ok:
                original_mkdir(self, parents=parents, exist_ok=True)
                raise FileExistsError(
                    f"[Errno 17] File exists: '{self}' (simulated TOCTOU race)"
                )

            return original_mkdir(self, parents=parents, exist_ok=True)

        storage = TodoStorage(str(db))
        todos = [Todo(id=1, text="test todo")]

        with patch.object(Path, "mkdir", mock_mkdir_race):
            # This should NOT raise an exception if the fix is correct
            storage.save(todos)

        # Verify the file was saved correctly
        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"

    def test_ensure_parent_directory_is_idempotent(self, tmp_path: Path) -> None:
        """Test that _ensure_parent_directory can be called multiple times
        without error, even if the directory already exists.
        """
        test_file = tmp_path / "subdir" / "test.json"

        # Call multiple times
        _ensure_parent_directory(test_file)
        _ensure_parent_directory(test_file)
        _ensure_parent_directory(test_file)

        # Verify parent exists
        assert test_file.parent.exists()
        assert test_file.parent.is_dir()

    def test_ensure_parent_directory_creates_nested_parents(self, tmp_path: Path) -> None:
        """Test that _ensure_parent_directory correctly creates nested parent directories."""
        test_file = tmp_path / "level1" / "level2" / "level3" / "test.json"

        _ensure_parent_directory(test_file)

        # Verify all parent directories were created
        assert (tmp_path / "level1").exists()
        assert (tmp_path / "level1" / "level2").exists()
        assert (tmp_path / "level1" / "level2" / "level3").exists()
