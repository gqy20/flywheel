"""Tests for automatic backup creation before saving.

This test suite verifies that TodoStorage creates backups before saving,
allowing users to recover from accidental data loss or corruption.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_after_save(tmp_path) -> None:
    """Test that a backup file is created after successful save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="original")]
    storage.save(todos)

    # Modify and save again - should create backup
    todos[0] = Todo(id=1, text="modified")
    storage.save(todos)

    # Verify backup file exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created after save"

    # Verify backup contains the original data
    backup_content = backup_path.read_text(encoding="utf-8")
    assert '"text": "original"' in backup_content
    assert '"text": "modified"' not in backup_content


def test_backup_rotation_keeps_only_n_backups(tmp_path) -> None:
    """Test that only N most recent backups are kept."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no backup created (no existing file)
    storage.save([Todo(id=1, text="version-0")])

    # Save multiple more times to create multiple backups
    for i in range(1, 6):  # 5 more saves (versions 1-5)
        todos = [Todo(id=1, text=f"version-{i}")]
        storage.save(todos)

    # Count backup files (todo.json.bak, .bak.1, .bak.2, etc.)
    backup_files = sorted(tmp_path.glob("todo.json.bak*"))
    assert len(backup_files) == 3, f"Expected 3 backup files, got {len(backup_files)}"

    # Verify the most recent backups exist
    assert (tmp_path / "todo.json.bak").exists()
    assert (tmp_path / "todo.json.bak.1").exists()
    assert (tmp_path / "todo.json.bak.2").exists()


def test_save_succeeds_even_if_backup_fails(tmp_path) -> None:
    """Test that save succeeds even if backup creation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="original")]
    storage.save(todos)

    # Mock shutil.copy2 to fail but save should still succeed
    with patch("flywheel.storage.shutil.copy2") as mock_copy:
        mock_copy.side_effect = OSError("Backup failed")

        # This should not raise an exception
        storage.save([Todo(id=1, text="modified")])

    # Verify the main file was updated (save succeeded despite backup failure)
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "modified"


def test_can_restore_from_backup(tmp_path) -> None:
    """Test that corrupted file can be restored from backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data (first save - no backup)
    initial_todos = [Todo(id=1, text="important"), Todo(id=2, text="data")]
    storage.save(initial_todos)

    # Save again to create backup (backup will contain 'important', 'data')
    storage.save([Todo(id=1, text="modified")])

    # Corrupt the main file
    db.write_text("{corrupted json data", encoding="utf-8")

    # Load should fail due to corrupted data
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Restore from backup
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists()

    # Copy backup to main file
    import shutil
    shutil.copy2(backup_path, db)

    # Load should now work with restored data from backup
    restored_todos = storage.load()
    assert len(restored_todos) == 2
    assert restored_todos[0].text == "important"
    assert restored_todos[1].text == "data"


def test_no_backup_on_first_save(tmp_path) -> None:
    """Test that no backup is created on first save (no existing file)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no existing file to backup
    storage.save([Todo(id=1, text="first")])

    # No backup should exist since there was no previous file
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup should be created on first save"


def test_backup_preserves_file_metadata(tmp_path) -> None:
    """Test that backup preserves file metadata (mtime, etc.)."""
    import time

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="original")]
    storage.save(todos)

    # Get original file mtime
    original_mtime = db.stat().st_mtime

    # Wait a bit to ensure timestamp difference
    time.sleep(0.01)

    # Save again to create backup
    storage.save([Todo(id=1, text="modified")])

    # Check backup exists and has similar mtime to original
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists()
    backup_mtime = backup_path.stat().st_mtime

    # Backup mtime should be close to original file's mtime before overwrite
    # (within 1 second due to filesystem precision)
    assert abs(backup_mtime - original_mtime) < 1.0
