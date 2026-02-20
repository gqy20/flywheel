"""Tests for backup file functionality before overwrite.

This test suite verifies that TodoStorage.save() creates a backup file
when FLYWHEEL_BACKUP=1 environment variable is set.

Regression test for issue #4682: Add backup file before overwrite
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupBeforeOverwrite:
    """Test backup functionality before file overwrite."""

    def test_backup_created_when_enabled(self, tmp_path: Path, monkeypatch) -> None:
        """Test that .bak file is created when FLYWHEEL_BACKUP=1."""
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        db = tmp_path / "todo.json"
        backup_file = tmp_path / ".todo.json.bak"
        storage = TodoStorage(str(db))

        # First save - creates initial file, no backup yet (no previous file)
        first_todos = [Todo(id=1, text="first save")]
        storage.save(first_todos)

        # Backup should not exist after first save (nothing to backup)
        assert not backup_file.exists()

        # Second save - should create backup of first save
        second_todos = [Todo(id=1, text="second save"), Todo(id=2, text="another")]
        storage.save(second_todos)

        # Backup should now exist
        assert backup_file.exists()

        # Backup should contain the first save data
        backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "first save"

        # Current file should have the second save data
        current_content = json.loads(db.read_text(encoding="utf-8"))
        assert len(current_content) == 2
        assert current_content[0]["text"] == "second save"

    def test_no_backup_when_disabled(self, tmp_path: Path, monkeypatch) -> None:
        """Test that no .bak file is created when FLYWHEEL_BACKUP is not set."""
        monkeypatch.delenv("FLYWHEEL_BACKUP", raising=False)

        db = tmp_path / "todo.json"
        backup_file = tmp_path / ".todo.json.bak"
        storage = TodoStorage(str(db))

        # First save
        first_todos = [Todo(id=1, text="first save")]
        storage.save(first_todos)

        # Second save
        second_todos = [Todo(id=1, text="second save")]
        storage.save(second_todos)

        # No backup should exist
        assert not backup_file.exists()

    def test_backup_preserves_previous_state(self, tmp_path: Path, monkeypatch) -> None:
        """Test that backup contains the state before the current save."""
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        db = tmp_path / "todo.json"
        backup_file = tmp_path / ".todo.json.bak"
        storage = TodoStorage(str(db))

        # Create multiple saves and verify backup chain
        for i in range(3):
            todos = [Todo(id=j, text=f"save-{i}-todo-{j}") for j in range(i + 1)]
            storage.save(todos)

            if i == 0:
                # After first save, no backup yet
                assert not backup_file.exists()
            else:
                # After subsequent saves, backup contains previous state
                backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
                assert len(backup_content) == i  # Previous save had i items
                assert backup_content[0]["text"] == f"save-{i - 1}-todo-0"

    def test_backup_with_custom_db_path(self, tmp_path: Path, monkeypatch) -> None:
        """Test that backup file naming works with custom database paths."""
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        db = custom_dir / "mydata.json"
        backup_file = custom_dir / ".mydata.json.bak"
        storage = TodoStorage(str(db))

        # First save
        storage.save([Todo(id=1, text="initial")])

        # Second save should create backup
        storage.save([Todo(id=1, text="updated")])

        assert backup_file.exists()
        backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
        assert backup_content[0]["text"] == "initial"

    def test_backup_works_with_atomic_write_failure(self, tmp_path: Path, monkeypatch) -> None:
        """Test that backup is created BEFORE write, so it's preserved on write failure."""
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        db = tmp_path / "todo.json"
        backup_file = tmp_path / ".todo.json.bak"
        storage = TodoStorage(str(db))

        # Create initial data
        initial_todos = [Todo(id=1, text="initial data")]
        storage.save(initial_todos)

        # Manually create backup (simulating what should happen in save())
        db.rename(backup_file)
        with open(db, "w") as f:
            json.dump([t.to_dict() for t in initial_todos], f)

        # Now backup exists with initial data
        assert backup_file.exists()
