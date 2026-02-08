"""Tests for file backup/rotation before overwriting (Issue #2114).

This test suite verifies that TodoStorage.save() creates backups
before overwriting the main file, allowing data recovery.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_with_backup_count_enabled(tmp_path) -> None:
    """Test that save() creates backup file when backup_count > 0."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_count=3)

    # Create initial todos
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save new todos - should create backup
    new_todos = [Todo(id=2, text="new")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_1 = tmp_path / "todo.json.1.bak"
    assert backup_1.exists(), "Backup file .1.bak should be created"

    # Verify backup contains original content
    backup_content = json.loads(backup_1.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original"


def test_save_rotates_backups_up_to_backup_count(tmp_path) -> None:
    """Test that backups are rotated correctly: 1 -> 2 -> 3 -> deleted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_count=3)

    # First save - no backup yet
    storage.save([Todo(id=1, text="v1")])

    # Second save - creates .1.bak
    storage.save([Todo(id=2, text="v2")])
    backup_1 = tmp_path / "todo.json.1.bak"
    assert backup_1.exists()
    assert json.loads(backup_1.read_text())[0]["text"] == "v1"

    # Third save - rotates .1.bak -> .2.bak, creates new .1.bak
    storage.save([Todo(id=3, text="v3")])
    backup_2 = tmp_path / "todo.json.2.bak"
    assert backup_2.exists()
    assert json.loads(backup_2.read_text())[0]["text"] == "v1"
    assert json.loads(backup_1.read_text())[0]["text"] == "v2"

    # Fourth save - rotates all, deletes oldest beyond backup_count
    storage.save([Todo(id=4, text="v4")])
    backup_3 = tmp_path / "todo.json.3.bak"
    assert backup_3.exists()
    assert json.loads(backup_3.read_text())[0]["text"] == "v1"
    assert json.loads(backup_2.read_text())[0]["text"] == "v2"
    assert json.loads(backup_1.read_text())[0]["text"] == "v3"

    # Fifth save - rotates all, .1(v1) was deleted at previous step
    # After this: .1.bak=v4, .2.bak=v3, .3.bak=v2, .4.bak(v2) deleted
    storage.save([Todo(id=5, text="v5")])
    assert backup_3.exists()
    assert json.loads(backup_3.read_text())[0]["text"] == "v2"
    assert json.loads(backup_2.read_text())[0]["text"] == "v3"
    assert json.loads(backup_1.read_text())[0]["text"] == "v4"


def test_backup_count_zero_disables_backups(tmp_path) -> None:
    """Test that backup_count=0 maintains backward compatibility (no backups)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_count=0)

    storage.save([Todo(id=1, text="v1")])
    storage.save([Todo(id=2, text="v2")])

    # No backup files should be created
    assert not (tmp_path / "todo.json.1.bak").exists()
    assert not (tmp_path / "todo.json.2.bak").exists()


def test_default_backup_count_is_zero(tmp_path) -> None:
    """Test that default behavior is no backups (backward compatibility)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # No backup_count specified

    storage.save([Todo(id=1, text="v1")])
    storage.save([Todo(id=2, text="v2")])

    # No backup files should be created by default
    assert not (tmp_path / "todo.json.1.bak").exists()


def test_backup_created_before_atomic_replace(tmp_path) -> None:
    """Test that backup contains content BEFORE the new save (original content)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_count=2)

    # Create initial file
    original = [Todo(id=1, text="original", done=False)]
    storage.save(original)

    # Save new content
    new = [Todo(id=2, text="new", done=True)]
    storage.save(new)

    # Backup should contain the ORIGINAL content, not the new content
    backup_1 = tmp_path / "todo.json.1.bak"
    backup_content = json.loads(backup_1.read_text())
    assert backup_content[0]["text"] == "original"
    assert backup_content[0]["done"] is False

    # Main file should have new content
    main_content = json.loads(db.read_text())
    assert main_content[0]["text"] == "new"
    assert main_content[0]["done"] is True


def test_backup_handles_nested_paths(tmp_path) -> None:
    """Test that backup works correctly with nested directory paths."""
    db = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db), backup_count=2)

    storage.save([Todo(id=1, text="v1")])
    storage.save([Todo(id=2, text="v2")])

    # Backup should be in same directory as main file
    backup_1 = tmp_path / "subdir" / "todo.json.1.bak"
    assert backup_1.exists()


def test_backup_failure_doesnt_prevent_save(tmp_path) -> None:
    """Test that if backup creation fails, the save still proceeds."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_count=2)

    # Create initial file
    storage.save([Todo(id=1, text="v1")])

    # Mock os.replace to fail only for backup files
    original_replace = __import__("os").replace

    def selective_replace(src, dst):
        # Fail if trying to create a backup (dst ends with .bak)
        if str(dst).endswith(".bak"):
            raise OSError("Backup creation failed")
        return original_replace(src, dst)

    with patch("flywheel.storage.os.replace", side_effect=selective_replace):
        # This should NOT raise - backup failure is handled gracefully
        storage.save([Todo(id=2, text="v2")])

    # Main file should still be saved with new content
    main_content = json.loads(db.read_text())
    assert main_content[0]["text"] == "v2"


def test_multiple_backups_preserve_chronological_order(tmp_path) -> None:
    """Test that multiple saves maintain correct chronological order in backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_count=5)

    # Create a series of saves
    for i in range(1, 7):
        storage.save([Todo(id=i, text=f"version-{i}")])

    # Check all backups exist and are in correct order
    for i in range(1, 6):  # We should have 5 backups (backup_count=5)
        backup = tmp_path / f"todo.json.{i}.bak"
        assert backup.exists(), f"Backup {i} should exist"
        content = json.loads(backup.read_text())
        # Backup i contains version (7 - i - 1) = oldest content
        # .1.bak has version 5, .2.bak has version 4, etc.
        expected_version = 6 - i
        assert content[0]["text"] == f"version-{expected_version}"

    # Version 1 should be deleted (oldest beyond backup_count)
    oldest_backup = tmp_path / "todo.json.5.bak"
    content = json.loads(oldest_backup.read_text())
    assert content[0]["text"] == "version-1"
