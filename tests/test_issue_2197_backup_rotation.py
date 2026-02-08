"""Tests for backup/rotation mechanism for corrupt or lost data recovery (Issue #2197).

This test suite verifies that TodoStorage.save() creates timestamped backup
files before overwriting existing data, with configurable max_backups parameter.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def _find_backup_files(db_path: Path) -> list[Path]:
    """Find all backup files for a given database file."""
    parent = db_path.parent
    pattern = re.compile(rf'^\.{db_path.name}\.backup\.(\d{{14}})$')
    backups = []
    for f in parent.iterdir():
        if f.is_file() and pattern.match(f.name):
            backups.append(f)
    return sorted(backups, key=lambda p: p.stat().st_mtime)


def test_save_creates_backup_when_file_exists(tmp_path) -> None:
    """Test that save creates a backup file when one exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="modified"), Todo(id=3, text="new")]
    storage.save(new_todos)

    # Verify backup was created
    backups = _find_backup_files(db)
    assert len(backups) >= 1, "Backup file should be created"

    # Verify backup contains original data
    backup_content = backups[0].read_text(encoding="utf-8")
    backup_data = json.loads(backup_content)
    assert len(backup_data) == 2
    assert backup_data[0]["text"] == "original"
    assert backup_data[1]["text"] == "data"

    # Verify current file has new data
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "modified"
    assert loaded[1].text == "new"


def test_no_backup_created_on_first_save(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - file doesn't exist
    todos = [Todo(id=1, text="first")]
    storage.save(todos)

    # Verify no backup was created
    backups = _find_backup_files(db)
    assert len(backups) == 0, "No backup should be created on first save"


def test_old_backups_cleaned_when_exceeding_max_backups(tmp_path) -> None:
    """Test that old backups are cleaned up when exceeding max_backups."""
    db = tmp_path / "todo.json"

    # Create storage with max_backups=2
    storage = TodoStorage(str(db), enable_backups=True, max_backups=2)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Create 4 more saves - should only keep 2 backups total
    for i in range(1, 5):
        storage.save([Todo(id=1, text=f"version{i}")])

    # Verify only max_backups exist
    backups = _find_backup_files(db)
    assert len(backups) <= 2, f"Should have at most 2 backups, got {len(backups)}"


def test_save_succeeds_even_if_backup_fails(tmp_path) -> None:
    """Test that save still succeeds even if backup creation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Mock shutil.copy to fail
    def failing_copy(*args, **kwargs):
        raise OSError("Backup failed")

    with patch("flywheel.storage.shutil.copy", failing_copy):
        # Save should still succeed
        new_todos = [Todo(id=1, text="modified")]
        storage.save(new_todos)

    # Verify current file was saved despite backup failure
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "modified"


def test_backup_has_timestamp_in_filename(tmp_path) -> None:
    """Test that backup filename includes timestamp."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Create initial data
    storage.save([Todo(id=1, text="original")])

    # Save again to create backup
    storage.save([Todo(id=1, text="modified")])

    # Verify backup filename pattern
    backups = _find_backup_files(db)
    assert len(backups) >= 1

    # Filename should match pattern: .todo.json.backup.YYYYMMDDHHMMSS
    pattern = re.compile(rf'^\.{db.name}\.backup\.(\d{{14}})$')
    assert pattern.match(backups[0].name), f"Backup filename {backups[0].name} doesn't match expected pattern"


def test_backup_disabled_by_default(tmp_path) -> None:
    """Test that backup creation is optional (disabled by default)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="original")])

    # Save again
    storage.save([Todo(id=1, text="modified")])

    # By default (enable_backups=False), no backup should be created
    backups = _find_backup_files(db)
    assert len(backups) == 0, "Backups should be disabled by default"


def test_backups_can_be_used_for_recovery(tmp_path) -> None:
    """Test that backups can be used to recover from corrupted data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Create good data
    good_todos = [Todo(id=1, text="good"), Todo(id=2, text="data")]
    storage.save(good_todos)

    # Save again to create backup
    storage.save([Todo(id=1, text="newer")])

    # Find the backup
    backups = _find_backup_files(db)
    assert len(backups) >= 1

    # Simulate corruption of main file
    db.write_text("corrupted data", encoding="utf-8")

    # Verify main file is corrupted
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Recover from backup
    backup_content = backups[0].read_text(encoding="utf-8")
    recovered_todos = [Todo.from_dict(item) for item in json.loads(backup_content)]

    assert len(recovered_todos) == 2
    assert recovered_todos[0].text == "good"
    assert recovered_todos[1].text == "data"
