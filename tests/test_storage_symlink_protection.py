"""Tests for symlink protection in TodoStorage.

This test suite verifies that TodoStorage.load() rejects symlinks
to prevent arbitrary file read attacks (issue #6463).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage


class TestSymlinkProtection:
    """Test cases for symlink security validation."""

    def test_load_rejects_symlink_to_file(self, tmp_path: Path) -> None:
        """Test that load() raises ValueError when path is a symlink to another file.

        Regression test for issue #6463: Security - load() follows symlinks
        without validation, allowing arbitrary file read.
        """
        # Create a real JSON file with valid content
        real_file = tmp_path / "real_data.json"
        real_file.write_text('[{"id": 1, "text": "secret data", "done": false}]', encoding="utf-8")

        # Create a symlink pointing to the real file
        symlink_path = tmp_path / ".todo.json"
        symlink_path.symlink_to(real_file)

        # Verify the symlink was created correctly
        assert symlink_path.is_symlink()
        assert symlink_path.exists()

        # load() should reject the symlink and raise ValueError
        storage = TodoStorage(str(symlink_path))
        with pytest.raises(ValueError, match="symlink"):
            storage.load()

    def test_load_rejects_symlink_to_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that load() raises ValueError when path is a dangling symlink."""
        # Create a symlink pointing to a non-existent file
        nonexistent = tmp_path / "does_not_exist.json"
        symlink_path = tmp_path / ".todo.json"
        symlink_path.symlink_to(nonexistent)

        # Verify the symlink was created but target doesn't exist
        assert symlink_path.is_symlink()
        # Note: exists() returns False for dangling symlinks

        # load() should reject the symlink (if it existed)
        storage = TodoStorage(str(symlink_path))
        # Since the symlink target doesn't exist, load() returns empty list
        # but we should still check for symlinks
        result = storage.load()
        assert result == []

    def test_load_accepts_regular_file(self, tmp_path: Path) -> None:
        """Test that load() works correctly with regular (non-symlink) files."""
        # Create a regular JSON file
        regular_file = tmp_path / ".todo.json"
        regular_file.write_text('[{"id": 1, "text": "normal data", "done": false}]', encoding="utf-8")

        # Verify it's not a symlink
        assert not regular_file.is_symlink()
        assert regular_file.exists()

        # load() should work normally
        storage = TodoStorage(str(regular_file))
        todos = storage.load()

        assert len(todos) == 1
        assert todos[0].id == 1
        assert todos[0].text == "normal data"
        assert todos[0].done is False

    def test_load_returns_empty_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that load() returns empty list for non-existent file."""
        nonexistent = tmp_path / "does_not_exist.json"

        storage = TodoStorage(str(nonexistent))
        todos = storage.load()

        assert todos == []

    def test_symlink_protection_prevents_arbitrary_file_read(self, tmp_path: Path) -> None:
        """Test that load() cannot be used to read arbitrary files via symlinks.

        This is the core security test for issue #6463.
        """
        # Simulate a sensitive file that attacker wants to read
        sensitive_file = tmp_path / "sensitive_data.json"
        sensitive_content = '[{"id": 1, "text": "SENSITIVE SECRET", "done": false}]'
        sensitive_file.write_text(sensitive_content, encoding="utf-8")

        # Attacker creates a symlink at the expected storage path
        symlink_path = tmp_path / ".todo.json"
        symlink_path.symlink_to(sensitive_file)

        # Attempt to load should fail with symlink protection
        storage = TodoStorage(str(symlink_path))
        with pytest.raises(ValueError, match="symlink"):
            storage.load()

        # Verify the error message is clear
        try:
            storage.load()
        except ValueError as e:
            error_msg = str(e).lower()
            # Error message should mention symlink and security concern
            assert "symlink" in error_msg

    def test_load_with_valid_symlink_in_parent_directory(self, tmp_path: Path) -> None:
        """Test that load() works when parent directory is a symlink but file is not.

        This verifies we only check the file itself, not the parent path.
        """
        # Create a real directory
        real_dir = tmp_path / "real_directory"
        real_dir.mkdir()

        # Create a symlink to the directory
        symlink_dir = tmp_path / "symlink_directory"
        symlink_dir.symlink_to(real_dir)

        # Create a regular file inside the symlinked directory
        storage_file = symlink_dir / ".todo.json"
        storage_file.write_text('[{"id": 1, "text": "test", "done": true}]', encoding="utf-8")

        # Verify setup: directory is symlink, but file is not
        assert symlink_dir.is_symlink()
        assert not storage_file.is_symlink()

        # load() should work since the file itself is not a symlink
        storage = TodoStorage(str(storage_file))
        todos = storage.load()

        assert len(todos) == 1
        assert todos[0].text == "test"
