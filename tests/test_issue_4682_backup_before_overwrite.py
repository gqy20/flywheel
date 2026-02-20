"""Tests for backup file feature before overwrite.

This test suite verifies that TodoStorage.save() creates a backup file
when FLYWHEEL_BACKUP=1 environment variable is set.

Issue: #4682
Feature: Add backup file before overwrite
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupBeforeOverwrite:
    """Test suite for backup file creation feature."""

    def test_backup_created_when_enabled_and_file_exists(self, tmp_path: Path) -> None:
        """Test that .bak file is created when FLYWHEEL_BACKUP=1 and file exists."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save - creates initial file
        first_todos = [Todo(id=1, text="first save")]
        storage.save(first_todos)

        # Second save - should create backup when enabled
        second_todos = [Todo(id=1, text="second save"), Todo(id=2, text="new todo")]
        with patch.dict(os.environ, {"FLYWHEEL_BACKUP": "1"}):
            storage.save(second_todos)

        # Verify backup file exists
        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists(), "Backup file should be created"

        # Verify backup contains first save data
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "first save"

    def test_no_backup_when_not_enabled(self, tmp_path: Path) -> None:
        """Test that no .bak file is created when FLYWHEEL_BACKUP is not set."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        first_todos = [Todo(id=1, text="first save")]
        storage.save(first_todos)

        # Second save - no backup when disabled
        second_todos = [Todo(id=1, text="second save")]
        # Ensure FLYWHEEL_BACKUP is not set
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FLYWHEEL_BACKUP", None)
            storage.save(second_todos)

        # Verify no backup file exists
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "Backup file should NOT be created when disabled"

    def test_no_backup_on_first_save(self, tmp_path: Path) -> None:
        """Test that no backup is created on first save (file doesn't exist yet)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save with backup enabled - no previous file to backup
        first_todos = [Todo(id=1, text="first save")]
        with patch.dict(os.environ, {"FLYWHEEL_BACKUP": "1"}):
            storage.save(first_todos)

        # Verify no backup file exists
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "Backup file should NOT be created on first save"

    def test_backup_overwrites_existing_backup(self, tmp_path: Path) -> None:
        """Test that existing .bak file is overwritten on subsequent saves."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        first_todos = [Todo(id=1, text="first save")]
        storage.save(first_todos)

        # Second save with backup
        second_todos = [Todo(id=1, text="second save")]
        with patch.dict(os.environ, {"FLYWHEEL_BACKUP": "1"}):
            storage.save(second_todos)

        # Third save with backup - should overwrite existing backup
        third_todos = [Todo(id=1, text="third save")]
        with patch.dict(os.environ, {"FLYWHEEL_BACKUP": "1"}):
            storage.save(third_todos)

        # Verify backup contains second save data (not first)
        backup_path = tmp_path / "todo.json.bak"
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 1
        assert backup_content[0]["text"] == "second save"

    def test_two_saves_backup_contains_first_data(self, tmp_path: Path) -> None:
        """Test that after two saves with backup, .bak contains first save data."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        first_todos = [Todo(id=1, text="alpha"), Todo(id=2, text="beta")]
        with patch.dict(os.environ, {"FLYWHEEL_BACKUP": "1"}):
            storage.save(first_todos)

        # Second save
        second_todos = [Todo(id=1, text="gamma")]
        with patch.dict(os.environ, {"FLYWHEEL_BACKUP": "1"}):
            storage.save(second_todos)

        # Verify backup contains first save's data
        backup_path = tmp_path / "todo.json.bak"
        backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
        assert len(backup_content) == 2
        texts = [t["text"] for t in backup_content]
        assert "alpha" in texts
        assert "beta" in texts
        assert "gamma" not in texts

    def test_backup_disabled_with_value_zero(self, tmp_path: Path) -> None:
        """Test that FLYWHEEL_BACKUP=0 does not create backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # First save
        first_todos = [Todo(id=1, text="first save")]
        storage.save(first_todos)

        # Second save with FLYWHEEL_BACKUP=0
        second_todos = [Todo(id=1, text="second save")]
        with patch.dict(os.environ, {"FLYWHEEL_BACKUP": "0"}):
            storage.save(second_todos)

        # Verify no backup file exists
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "Backup file should NOT be created when FLYWHEEL_BACKUP=0"
