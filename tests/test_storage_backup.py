"""Tests for file backup mechanism in TodoStorage.

This test suite verifies that TodoStorage can optionally create backup files
before saving, preserving previous versions for recovery purposes.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupDisabled:
    """Tests for default behavior when backup=False."""

    def test_no_backup_file_created_by_default(self, tmp_path: Path) -> None:
        """Test that backup=False (default) creates no .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # No backup should exist
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists()

    def test_explicit_backup_false_creates_no_backup(self, tmp_path: Path) -> None:
        """Test that explicit backup=False creates no .bak file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=False)

        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists()


class TestBackupEnabled:
    """Tests for backup behavior when backup=True."""

    def test_backup_created_when_backup_true(self, tmp_path: Path) -> None:
        """Test that backup=True creates .bak file with previous data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # First save - no backup since no previous file
        todos_v1 = [Todo(id=1, text="version 1")]
        storage.save(todos_v1)

        backup_path = tmp_path / "todo.json.bak"
        # First save should not create backup (no previous file exists)
        assert not backup_path.exists()

        # Second save - should create backup with v1 data
        todos_v2 = [Todo(id=1, text="version 2"), Todo(id=2, text="new")]
        storage.save(todos_v2)

        # Backup should now exist with v1 data
        assert backup_path.exists()

        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_data) == 1
        assert backup_data[0]["text"] == "version 1"

    def test_backup_contains_previous_version(self, tmp_path: Path) -> None:
        """Test that .bak contains the data from the previous save."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # Multiple saves
        for i in range(3):
            todos = [Todo(id=j, text=f"iteration-{i}-task-{j}") for j in range(1, i + 2)]
            storage.save(todos)

        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists()

        backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
        # Backup should contain second-to-last data (iteration 1 with 2 tasks)
        # Note: First save (i=0) doesn't create backup (no existing file)
        # i=1 save creates backup of i=0 data
        # i=2 save overwrites backup with i=1 data
        assert len(backup_data) == 2
        assert backup_data[0]["text"] == "iteration-1-task-1"

    def test_backup_file_permissions_match_original(self, tmp_path: Path) -> None:
        """Test that .bak file permissions match the original file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # First save
        todos = [Todo(id=1, text="initial")]
        storage.save(todos)

        # Get original file permissions
        original_mode = db.stat().st_mode

        # Second save (creates backup)
        todos2 = [Todo(id=1, text="updated")]
        storage.save(todos2)

        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists()

        # Permissions should match
        backup_mode = backup_path.stat().st_mode
        assert backup_mode == original_mode

    def test_first_save_creates_no_empty_backup(self, tmp_path: Path) -> None:
        """Test that first save (no existing file) does not create empty backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # First save with no pre-existing file
        todos = [Todo(id=1, text="first")]
        storage.save(todos)

        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists()

    def test_backup_failure_does_not_block_save(self, tmp_path: Path) -> None:
        """Test that backup failure logs warning but doesn't block save."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup=True)

        # First save to create initial file
        todos1 = [Todo(id=1, text="initial")]
        storage.save(todos1)

        # Make the backup path unwritable to simulate backup failure
        backup_path = tmp_path / "todo.json.bak"
        # Create a directory with same name to cause backup to fail
        backup_path.mkdir()
        try:
            # Second save should still succeed despite backup failure
            todos2 = [Todo(id=1, text="updated")]
            storage.save(todos2)

            # Main file should be updated
            loaded = storage.load()
            assert len(loaded) == 1
            assert loaded[0].text == "updated"
        finally:
            # Cleanup - remove directory and its contents
            shutil.rmtree(backup_path, ignore_errors=True)
