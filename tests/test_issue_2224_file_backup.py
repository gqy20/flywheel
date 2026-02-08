"""Tests for file backup feature in TodoStorage.save() - Issue #2224.

This test suite verifies that TodoStorage.save() creates backups of the
previous file content before overwriting, allowing users to recover from
buggy code writes.

Test Strategy: RED-GREEN-TDD
- RED: Write failing tests first (this file)
- GREEN: Implement backup mechanism to make tests pass
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_after_save(tmp_path) -> None:
    """Test that a .bak file with timestamp is created after save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="updated task", done=True)]
    storage.save(new_todos)

    # Verify backup file was created with .bak extension
    backup_files = list(db.parent.glob("*.json.bak-*"))
    assert len(backup_files) >= 1, "At least one backup file should be created"

    # Verify backup file has timestamp in name
    backup_name = backup_files[0].name
    assert backup_name.startswith("todo.json.bak-"), "Backup should have .bak- prefix with timestamp"


def test_backup_contains_previous_content(tmp_path) -> None:
    """Test that backup contains the content from before the save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data with specific content
    original_todos = [Todo(id=1, text="original content"), Todo(id=2, text="keep this")]
    storage.save(original_todos)

    # Get the original file content for comparison
    original_content = json.dumps(
        [todo.to_dict() for todo in original_todos],
        ensure_ascii=False,
        indent=2,
    )

    # Save new data
    new_todos = [Todo(id=3, text="new content")]
    storage.save(new_todos)

    # Find backup file
    backup_files = list(db.parent.glob("*.json.bak-*"))
    assert len(backup_files) >= 1, "Backup file should exist"

    # Verify backup contains the original content
    backup_content = backup_files[0].read_text(encoding="utf-8")
    assert backup_content == original_content, "Backup should contain previous file content"


def test_only_last_3_backups_kept(tmp_path) -> None:
    """Test that only the last 3 backups are kept, older ones are auto-deleted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Perform 5 saves to create 5 potential backups
    for i in range(5):
        todos = [Todo(id=i, text=f"save {i}")]
        storage.save(todos)

    # Verify only 3 backup files exist (most recent)
    backup_files = sorted(db.parent.glob("*.json.bak-*"))
    assert len(backup_files) <= 3, f"Only 3 backups should be kept, got {len(backup_files)}"


def test_enable_backup_false_disables_backup(tmp_path) -> None:
    """Test that enable_backup=False parameter disables backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backup=False)

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save new data - should NOT create backup
    new_todos = [Todo(id=2, text="new")]
    storage.save(new_todos)

    # Verify NO backup file was created
    backup_files = list(db.parent.glob("*.json.bak-*"))
    assert len(backup_files) == 0, "No backup files should be created when enable_backup=False"


def test_backup_env_var_disables_backup(tmp_path, monkeypatch) -> None:
    """Test that FLYWHEEL_ENABLE_BACKUP=0 disables backup creation."""
    # Set environment variable to disable backups
    monkeypatch.setenv("FLYWHEEL_ENABLE_BACKUP", "0")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save new data - should NOT create backup due to env var
    new_todos = [Todo(id=2, text="new")]
    storage.save(new_todos)

    # Verify NO backup file was created
    backup_files = list(db.parent.glob("*.json.bak-*"))
    assert len(backup_files) == 0, "No backup files should be created when FLYWHEEL_ENABLE_BACKUP=0"


def test_backup_not_created_on_first_save(tmp_path) -> None:
    """Test that backup is NOT created on first save (no previous file)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no previous file exists
    todos = [Todo(id=1, text="first save")]
    storage.save(todos)

    # Verify NO backup file was created (nothing to backup)
    backup_files = list(db.parent.glob("*.json.bak-*"))
    assert len(backup_files) == 0, "No backup should be created on first save"


def test_backup_with_custom_max_backups(tmp_path) -> None:
    """Test that max_backups parameter controls number of backups kept."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=2)

    # Perform 5 saves
    for i in range(5):
        todos = [Todo(id=i, text=f"save {i}")]
        storage.save(todos)

    # Verify only 2 backup files exist
    backup_files = sorted(db.parent.glob("*.json.bak-*"))
    assert len(backup_files) <= 2, f"Only 2 backups should be kept, got {len(backup_files)}"
