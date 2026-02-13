"""Security tests for symlink handling in TodoStorage.

This test suite verifies that TodoStorage.load() safely handles symlinks
to prevent TOCTOU (Time-of-Check to Time-of-Use) race condition attacks.

Issue: #3103 - load() method uses path.exists() which follows symlinks,
allowing TOCTOU race condition.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestSymlinkSecurity:
    """Test that load() rejects symlinks to prevent TOCTOU attacks."""

    def test_load_rejects_symlink_to_valid_file(self, tmp_path: Path) -> None:
        """Regression test for #3103: load() should reject symlinks.

        An attacker could create a symlink pointing to a sensitive file.
        The application should detect and reject the symlink rather than
        following it.
        """
        # Create a valid JSON file with legitimate todos
        real_file = tmp_path / "real_todos.json"
        real_todos = [Todo(id=1, text="legitimate todo")]
        real_storage = TodoStorage(str(real_file))
        real_storage.save(real_todos)

        # Create a symlink pointing to the real file
        symlink_path = tmp_path / "symlink_todos.json"
        symlink_path.symlink_to(real_file)

        # Attempting to load from symlink should raise an error
        symlink_storage = TodoStorage(str(symlink_path))
        with pytest.raises(ValueError, match="symlink"):
            symlink_storage.load()

    def test_load_rejects_symlink_to_nonexistent_target(self, tmp_path: Path) -> None:
        """Regression test for #3103: load() should reject dangling symlinks.

        A dangling symlink (pointing to non-existent target) could be
        exploited in a TOCTOU attack if an attacker creates the target
        after the initial check.
        """
        # Create a symlink pointing to a non-existent file
        nonexistent = tmp_path / "nonexistent.json"
        symlink_path = tmp_path / "dangling_symlink.json"
        symlink_path.symlink_to(nonexistent)

        # Attempting to load from dangling symlink should raise an error
        symlink_storage = TodoStorage(str(symlink_path))
        with pytest.raises(ValueError, match="symlink"):
            symlink_storage.load()

    def test_load_accepts_regular_file(self, tmp_path: Path) -> None:
        """Verify that load() still works for regular files after symlink fix."""
        # Create a regular file with valid JSON
        db_path = tmp_path / "regular_todos.json"
        todos = [Todo(id=1, text="regular todo"), Todo(id=2, text="another todo")]
        storage = TodoStorage(str(db_path))
        storage.save(todos)

        # Loading from regular file should work
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "regular todo"
        assert loaded[1].text == "another todo"

    def test_load_returns_empty_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Verify load() returns empty list for non-existent regular paths."""
        nonexistent = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(nonexistent))
        result = storage.load()
        assert result == []

    def test_load_direct_symlink_vs_resolved_path(self, tmp_path: Path) -> None:
        """Test that resolving a symlink path still detects the symlink.

        This verifies that the check uses the original path, not a resolved path.
        """
        # Create a valid JSON file
        real_file = tmp_path / "real_todos.json"
        real_todos = [Todo(id=1, text="legitimate todo")]
        real_storage = TodoStorage(str(real_file))
        real_storage.save(real_todos)

        # Create a symlink
        symlink_path = tmp_path / "symlink_todos.json"
        symlink_path.symlink_to(real_file)

        # Even if we access via the symlink path, it should be detected
        symlink_storage = TodoStorage(str(symlink_path))
        with pytest.raises(ValueError, match="symlink"):
            symlink_storage.load()

        # But the real file should still work
        real_storage2 = TodoStorage(str(real_file))
        loaded = real_storage2.load()
        assert len(loaded) == 1
        assert loaded[0].text == "legitimate todo"
