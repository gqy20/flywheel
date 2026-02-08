"""Tests for file backup feature (Issue #2224)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileBackup:
    """Tests for automatic file backup before overwriting."""

    def test_save_creates_backup_with_timestamp(self, tmp_path: Path) -> None:
        """Test that save() creates a .bak file with timestamp after successful save."""
        db_path = tmp_path / "todo.json"
        storage = TodoStorage(str(db_path))

        # Create initial content
        todos = [Todo(id=1, text="First task")]
        storage.save(todos)

        # Save again - should create backup
        todos = [Todo(id=1, text="Updated task")]
        storage.save(todos)

        # Check backup file was created with timestamp pattern
        backup_files = list(db_path.parent.glob("todo.json.*.bak"))
        assert len(backup_files) >= 1, "No backup file was created"

        # Verify timestamp format (YYYYMMDDHHMMSSffffff)
        backup_name = backup_files[0].name
        timestamp_pattern = r"todo\.json\.(\d{20})\.bak"
        match = re.search(timestamp_pattern, backup_name)
        assert match is not None, f"Backup file name doesn't match expected pattern: {backup_name}"

    def test_backup_contains_previous_content(self, tmp_path: Path) -> None:
        """Test that backup contains the content from before the new save."""
        db_path = tmp_path / "todo.json"
        storage = TodoStorage(str(db_path))

        # Create initial content
        initial_todos = [Todo(id=1, text="Original task")]
        storage.save(initial_todos)

        # Save new content
        updated_todos = [Todo(id=1, text="Modified task")]
        storage.save(updated_todos)

        # Find backup file and verify it contains original content
        backup_files = list(db_path.parent.glob("todo.json.*.bak"))
        assert len(backup_files) >= 1

        backup_content = json.loads(backup_files[0].read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "Original task"

    def test_only_keeps_last_3_backups(self, tmp_path: Path) -> None:
        """Test that only the last 3 backups are kept, oldest deleted when exceeding limit."""
        db_path = tmp_path / "todo.json"
        storage = TodoStorage(str(db_path))

        # Save 5 times - should only keep 3 backups
        for i in range(5):
            todos = [Todo(id=1, text=f"Task version {i}")]
            storage.save(todos)

        backup_files = sorted(db_path.parent.glob("todo.json.*.bak"))

        # Should have exactly 3 backups (last 3 saves)
        assert len(backup_files) == 3, f"Expected 3 backups, found {len(backup_files)}"

    def test_enable_backup_false_disables_backup(self, tmp_path: Path) -> None:
        """Test that enable_backup=False disables backup creation."""
        db_path = tmp_path / "todo.json"
        storage = TodoStorage(str(db_path), enable_backup=False)

        # Save twice
        todos = [Todo(id=1, text="First task")]
        storage.save(todos)
        todos = [Todo(id=1, text="Second task")]
        storage.save(todos)

        # Check no backup files were created
        backup_files = list(db_path.parent.glob("*.bak"))
        assert len(backup_files) == 0, "Backup files should not be created when enable_backup=False"

    def test_first_save_creates_no_backup(self, tmp_path: Path) -> None:
        """Test that first save (when file doesn't exist) doesn't create backup."""
        db_path = tmp_path / "todo.json"
        storage = TodoStorage(str(db_path))

        # First save - file doesn't exist yet
        todos = [Todo(id=1, text="First task")]
        storage.save(todos)

        # Check no backup files were created
        backup_files = list(db_path.parent.glob("*.bak"))
        assert len(backup_files) == 0, "No backup should be created on first save"
