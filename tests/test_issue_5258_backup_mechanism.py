"""Tests for file backup mechanism in TodoStorage.

This test suite verifies the backup feature for issue #5258:
- backup=False (default) maintains current behavior (no backup)
- backup=True creates .bak file before save
- Backup failure doesn't block main save flow
- .bak file permissions match original file
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupDisabled:
    """Tests for default backup=False behavior."""

    def test_no_backup_file_created_when_backup_false(self, tmp_path: Path) -> None:
        """Verify backup=False (default) does not create .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # No .bak file should exist
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists()

    def test_no_backup_file_created_with_explicit_false(self, tmp_path: Path) -> None:
        """Verify explicitly setting backup=False doesn't create .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=False)

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists()


class TestBackupEnabled:
    """Tests for backup=True behavior."""

    def test_backup_created_when_file_exists(self, tmp_path: Path) -> None:
        """Verify .bak file is created when saving over existing file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # First save - no backup yet (file doesn't exist)
        first_todos = [Todo(id=1, text="first")]
        storage.save(first_todos)

        backup_path = tmp_path / "todo.json.bak"
        # No backup yet since file didn't exist before first save
        assert not backup_path.exists()

        # Second save - should create backup of first
        second_todos = [Todo(id=1, text="second"), Todo(id=2, text="added")]
        storage.save(second_todos)

        # Now backup should exist with first save's data
        assert backup_path.exists()
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "first"

    def test_backup_contains_previous_version(self, tmp_path: Path) -> None:
        """Verify .bak file contains previous version's data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # Initial save
        storage.save([Todo(id=1, text="v1")])

        # Overwrite - creates backup of v1
        storage.save([Todo(id=1, text="v2")])

        # Another overwrite - creates backup of v2
        storage.save([Todo(id=1, text="v3"), Todo(id=2, text="new")])

        # Backup should now contain v2 data
        backup_path = tmp_path / "todo.json.bak"
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "v2"

    def test_no_backup_on_first_save(self, tmp_path: Path) -> None:
        """Verify first save (no existing file) doesn't create empty backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # First save with backup=True
        storage.save([Todo(id=1, text="first")])

        backup_path = tmp_path / "todo.json.bak"
        # No backup should be created when no file existed before
        assert not backup_path.exists()


class TestBackupFailureHandling:
    """Tests for backup failure handling."""

    def test_backup_failure_does_not_block_save(self, tmp_path: Path) -> None:
        """Verify backup failure logs warning but doesn't block main save."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # Create initial file
        storage.save([Todo(id=1, text="initial")])

        # Mock shutil.copy2 to fail
        with patch("shutil.copy2") as mock_copy:
            mock_copy.side_effect = OSError("Backup failed")

            # Save should still succeed despite backup failure
            storage.save([Todo(id=1, text="updated")])

        # Verify main file was updated despite backup failure
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "updated"


class TestBackupPermissions:
    """Tests for backup file permissions."""

    def test_backup_file_permissions_match_original(self, tmp_path: Path) -> None:
        """Verify .bak file has same permissions as original file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # Create initial file
        storage.save([Todo(id=1, text="initial")])

        # Get original file permissions
        original_mode = db.stat().st_mode

        # Trigger backup creation
        storage.save([Todo(id=1, text="updated")])

        backup_path = tmp_path / "todo.json.bak"
        backup_mode = backup_path.stat().st_mode

        # Permissions should match
        assert stat.S_IMODE(backup_mode) == stat.S_IMODE(original_mode)
