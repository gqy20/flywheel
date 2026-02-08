"""Tests for backup and rollback functionality in TodoStorage.

This test suite verifies that TodoStorage creates backups before save operations
and can rollback from backup when needed.
"""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupCreation:
    """Tests for automatic backup file creation."""

    def test_backup_created_before_save(self, tmp_path) -> None:
        """Test that a backup file is created with timestamp before save operation."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        initial_todos = [Todo(id=1, text="initial")]
        storage.save(initial_todos)

        # Modify and save again - should create backup
        modified_todos = [Todo(id=1, text="modified"), Todo(id=2, text="new")]
        storage.save(modified_todos)

        # Verify backup file was created
        backup_pattern = re.compile(r"todo\.json\.bak\.\d+")
        backups = [f for f in tmp_path.glob("todo.json.bak.*") if backup_pattern.match(f.name)]

        assert len(backups) == 1, f"Expected 1 backup file, found {len(backups)}: {backups}"

        # Verify backup contains original data
        backup_content = backups[0].read_text(encoding="utf-8")
        assert '"text": "initial"' in backup_content

    def test_backup_filename_contains_timestamp(self, tmp_path) -> None:
        """Test that backup filename includes timestamp in format .bak.{timestamp}."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data and save
        storage.save([Todo(id=1, text="test")])

        # Save again to create backup
        storage.save([Todo(id=1, text="modified")])

        # Find backup file
        backups = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backups) == 1

        # Verify filename pattern: todo.json.bak.{timestamp}
        backup_name = backups[0].name
        assert backup_name.startswith("todo.json.bak.")

        # Extract and verify timestamp is numeric
        timestamp_str = backup_name.replace("todo.json.bak.", "")
        assert timestamp_str.isdigit(), f"Timestamp should be numeric, got: {timestamp_str}"


class TestBackupRetention:
    """Tests for backup retention limit and cleanup."""

    def test_retention_limit_keeps_latest_backups(self, tmp_path) -> None:
        """Test that only the most recent backups are kept up to retention limit."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_retention=3)

        # Create initial data
        storage.save([Todo(id=1, text="initial")])

        # Save 5 times to create 5 backups (mock time to ensure unique timestamps)
        current_time = 1000
        for i in range(5):
            with patch("flywheel.storage.time.time", return_value=current_time):
                storage.save([Todo(id=1, text=f"version-{i}")])
                current_time += 1

        # Should only keep 3 most recent backups (retention limit)
        backups = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backups) == 3, f"Expected 3 backups (retention limit), found {len(backups)}"

    def test_oldest_backups_deleted_first(self, tmp_path) -> None:
        """Test that oldest backups are deleted when exceeding retention limit."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_retention=2)

        # Create initial data (no backup on first save)
        storage.save([Todo(id=1, text="version-0")])

        # Save multiple times to create backups (mock time for unique timestamps)
        current_time = 2000
        for i in range(1, 5):  # Save version-1 through version-4
            with patch("flywheel.storage.time.time", return_value=current_time):
                storage.save([Todo(id=1, text=f"version-{i}")])
                current_time += 1

        # Get all backups and sort by modification time
        backups = sorted(tmp_path.glob("todo.json.bak.*"), key=lambda p: p.stat().st_mtime)

        # Should only have 2 backups (retention limit)
        assert len(backups) == 2

        # Verify oldest backups were deleted by checking content
        # The remaining backups should be for the most recent versions
        backup_contents = [b.read_text(encoding="utf-8") for b in backups]

        # Check that version-0 and version-1 backups are gone (oldest), version-2 and version-3 remain
        assert not any('"version-0"' in content for content in backup_contents), "Oldest backup (version-0) should be deleted"
        assert not any('"version-1"' in content for content in backup_contents), "Second oldest backup (version-1) should be deleted"
        # We should have version-2 and version-3 in the remaining backups
        assert any('"version-2"' in content for content in backup_contents), "Should have version-2 backup"
        assert any('"version-3"' in content for content in backup_contents), "Should have version-3 backup"

    def test_default_retention_is_five(self, tmp_path) -> None:
        """Test that default retention limit is 5 backups."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))  # No explicit retention parameter

        # Create initial data
        storage.save([Todo(id=1, text="initial")])

        # Save 7 times to create 7 backups (mock time to ensure unique timestamps)
        current_time = 3000
        for i in range(7):
            with patch("flywheel.storage.time.time", return_value=current_time):
                storage.save([Todo(id=1, text=f"version-{i}")])
                current_time += 1

        # Should default to keeping 5 most recent backups
        backups = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backups) == 5, f"Expected 5 backups (default), found {len(backups)}"


class TestRollback:
    """Tests for rollback functionality."""

    def test_rollback_restores_from_backup(self, tmp_path) -> None:
        """Test that rollback() method successfully restores data from backup file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial data
        original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
        storage.save(original_todos)

        # Modify and save to create backup
        modified_todos = [Todo(id=1, text="modified")]
        storage.save(modified_todos)

        # Get the backup file path
        backups = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backups) == 1

        # Rollback to backup
        storage.rollback(backups[0])

        # Verify data was restored
        restored = storage.load()
        assert len(restored) == 2
        assert restored[0].text == "original"
        assert restored[1].text == "data"

    def test_rollback_with_invalid_backup_path_raises_error(self, tmp_path) -> None:
        """Test that rollback with non-existent backup path raises appropriate error."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create some data
        storage.save([Todo(id=1, text="test")])

        # Try to rollback from non-existent backup
        fake_backup = tmp_path / "todo.json.bak.9999999999"

        with pytest.raises(FileNotFoundError):
            storage.rollback(fake_backup)

    def test_rollback_preserves_backup_file(self, tmp_path) -> None:
        """Test that rollback operation doesn't delete the backup file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial and modified data
        storage.save([Todo(id=1, text="original")])
        storage.save([Todo(id=1, text="modified")])

        # Get backup
        backups = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backups) == 1
        backup_path = backups[0]

        # Rollback
        storage.rollback(backup_path)

        # Verify backup still exists
        assert backup_path.exists(), "Backup file should still exist after rollback"

    def test_rollback_after_multiple_saves(self, tmp_path) -> None:
        """Test rollback to specific backup when multiple backups exist."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), backup_retention=5)

        # Create initial version
        v1_todos = [Todo(id=1, text="version-1")]
        storage.save(v1_todos)

        # Save multiple times creating multiple backups (mock time for unique timestamps)
        current_time = 5000
        v2_todos = [Todo(id=1, text="version-2")]
        with patch("flywheel.storage.time.time", return_value=current_time):
            storage.save(v2_todos)

        current_time = 5001
        v3_todos = [Todo(id=1, text="version-3")]
        with patch("flywheel.storage.time.time", return_value=current_time):
            storage.save(v3_todos)

        # Get all backups sorted by modification time (oldest first)
        backups = sorted(tmp_path.glob("todo.json.bak.*"), key=lambda p: p.stat().st_mtime)

        # Rollback to oldest backup (version-1)
        storage.rollback(backups[0])

        # Verify we got version-1 data
        restored = storage.load()
        assert len(restored) == 1
        assert restored[0].text == "version-1"


class TestBackupIntegration:
    """Integration tests for backup functionality with existing atomic save."""

    def test_backup_works_with_atomic_save(self, tmp_path) -> None:
        """Test that backup creation doesn't interfere with atomic save behavior."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save data
        storage.save([Todo(id=1, text="test data")])

        # Verify atomic behavior: temp file cleaned up
        temp_files = list(tmp_path.glob(".todo.json.*.tmp"))
        assert len(temp_files) == 0, "Temp files should be cleaned up"

        # Verify backup was created and main file exists
        backups = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backups) == 0, "No backup on first save (nothing to backup yet)"
        assert db.exists(), "Main file should exist"

        # Save again - should create backup
        storage.save([Todo(id=1, text="modified")])

        backups = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backups) == 1, "Backup should be created on second save"

        # Verify both files have valid content
        main_content = db.read_text(encoding="utf-8")
        backup_content = backups[0].read_text(encoding="utf-8")

        assert '"test data"' in backup_content, "Backup should have original data"
        assert '"modified"' in main_content, "Main file should have new data"

    def test_backup_on_first_save_no_existing_file(self, tmp_path) -> None:
        """Test that no backup is created on first save when file doesn't exist."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save - file doesn't exist yet
        storage.save([Todo(id=1, text="first")])

        # Should not create backup (nothing to backup)
        backups = list(tmp_path.glob("todo.json.bak.*"))
        assert len(backups) == 0, "No backup should be created on first save"
