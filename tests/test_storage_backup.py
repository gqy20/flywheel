"""Tests for automatic backup behavior in TodoStorage.

This test suite verifies that TodoStorage.save() creates a backup file
before overwriting existing data, providing a recovery path when users
accidentally delete/overwrite todos.

Issue #5406: Add automatic backup before overwrite
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupBeforeOverwrite:
    """Tests for automatic backup creation before overwrite."""

    def test_save_creates_backup_when_file_exists(self, tmp_path: Path) -> None:
        """Test that save() creates .bak file before overwriting existing file.

        Acceptance criteria: save() creates .bak file before overwriting when
        original exists.
        """
        db = tmp_path / "todo.json"
        backup_path = tmp_path / "todo.json.bak"
        storage = TodoStorage(str(db))

        # First save - creates initial file
        first_todos = [Todo(id=1, text="first todo"), Todo(id=2, text="second todo")]
        storage.save(first_todos)

        # Second save - should create backup before overwriting
        second_todos = [Todo(id=1, text="replaced todo")]
        storage.save(second_todos)

        # Verify backup file was created
        assert backup_path.exists(), "Backup file should be created before overwrite"

        # Verify backup contains first save's content
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 2
        assert backup_content[0]["text"] == "first todo"
        assert backup_content[1]["text"] == "second todo"

    def test_save_on_new_file_does_not_create_backup(self, tmp_path: Path) -> None:
        """Test that save() does not create .bak file when saving new file.

        Acceptance criteria: save on new file does not create .bak
        """
        db = tmp_path / "todo.json"
        backup_path = tmp_path / "todo.json.bak"
        storage = TodoStorage(str(db))

        # First save on new file - should NOT create backup
        todos = [Todo(id=1, text="initial todo")]
        storage.save(todos)

        # Verify no backup file was created
        assert not backup_path.exists(), "Backup file should not be created for new file"

    def test_backup_has_same_permissions_as_original(self, tmp_path: Path) -> None:
        """Test that backup file preserves original file's permissions.

        Acceptance criteria: Backup file has same permissions as original
        """
        db = tmp_path / "todo.json"
        backup_path = tmp_path / "todo.json.bak"
        storage = TodoStorage(str(db))

        # Create initial file
        todos = [Todo(id=1, text="original")]
        storage.save(todos)

        # Get original permissions
        original_mode = db.stat().st_mode

        # Save again to trigger backup
        storage.save([Todo(id=1, text="updated")])

        # Verify backup has same permissions
        backup_mode = backup_path.stat().st_mode
        # Compare permission bits (ignore file type)
        assert stat.S_IMODE(backup_mode) == stat.S_IMODE(original_mode), (
            f"Backup permissions {oct(stat.S_IMODE(backup_mode))} "
            f"should match original {oct(stat.S_IMODE(original_mode))}"
        )

    def test_backup_rotation_keeps_only_one_backup(self, tmp_path: Path) -> None:
        """Test that only one backup file is kept (rotation).

        Acceptance criteria: Backup rotation keeps only 1 backup file
        """
        db = tmp_path / "todo.json"
        backup_path = tmp_path / "todo.json.bak"
        storage = TodoStorage(str(db))

        # First save
        storage.save([Todo(id=1, text="version 1")])
        # Second save - creates backup of version 1
        storage.save([Todo(id=1, text="version 2")])
        # Third save - should rotate: backup now contains version 2
        storage.save([Todo(id=1, text="version 3")])

        # Verify only one backup file exists
        bak_files = list(tmp_path.glob("*.bak"))
        assert len(bak_files) == 1, f"Should have exactly 1 backup file, found {len(bak_files)}"

        # Verify backup contains version 2 (not version 1)
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert backup_content[0]["text"] == "version 2", (
            "Backup should contain the most recent previous version"
        )

    def test_current_file_contains_latest_data(self, tmp_path: Path) -> None:
        """Test that current file always contains the latest saved data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save multiple times
        storage.save([Todo(id=1, text="version 1")])
        storage.save([Todo(id=1, text="version 2")])
        storage.save([Todo(id=1, text="version 3"), Todo(id=2, text="new")])

        # Verify current file has latest content
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "version 3"
        assert loaded[1].text == "new"
