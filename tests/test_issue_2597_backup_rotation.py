"""Tests for file backup/rotation before overwriting existing data (Issue #2597).

This test suite verifies that TodoStorage creates backup files before overwriting
existing data, with proper rotation to keep only the last N backups.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_on_overwrite(tmp_path) -> None:
    """Verify .bak file created when overwriting existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Overwrite with new data
    new_todos = [Todo(id=1, text="modified")]
    storage.save(new_todos)

    # Verify backup was created
    backup = db.with_suffix(".json.bak")
    assert backup.exists(), "Backup file should be created"

    # Verify backup contains original data
    backup_content = json.loads(backup.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original"


def test_first_save_creates_no_backup(tmp_path) -> None:
    """Verify first save (no existing file) creates no backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="first todo")]
    storage.save(todos)

    # Verify no backup was created for first save
    backup = db.with_suffix(".json.bak")
    assert not backup.exists(), "No backup should be created on first save"


def test_backup_rotation_keeps_only_last_n(tmp_path) -> None:
    """Verify backup rotation keeps only last N backups (default 3)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create multiple saves to generate backups
    for i in range(5):
        todos = [Todo(id=1, text=f"version-{i}")]
        storage.save(todos)

    # Check that only the last 3 backups exist (default rotation)
    parent_dir = tmp_path
    bak_files = sorted(parent_dir.glob("todo.json.bak*"))

    # Should have .bak, .bak.1, .bak.2 (3 backups total)
    assert len(bak_files) == 3, f"Expected 3 backups, got {len(bak_files)}: {bak_files}"

    # Verify the backups contain the right versions (newest = .bak, oldest = .bak.2)
    newest_backup = db.with_suffix(".json.bak")
    backup_content = json.loads(newest_backup.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version-3", "Newest backup should have version 3"


def test_backup_has_correct_permissions(tmp_path) -> None:
    """Verify backup file has 0o600 permissions (owner read/write only)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="original")])

    # Overwrite to create backup
    storage.save([Todo(id=1, text="modified")])

    backup = db.with_suffix(".json.bak")
    assert backup.exists()

    # Check permissions are 0o600 (rw-------)
    backup_stat = backup.stat()
    backup_mode = backup_stat.st_mode & 0o777
    assert backup_mode == 0o600, f"Backup should have 0o600 permissions, got {oct(backup_mode)}"


def test_backup_contains_valid_json(tmp_path) -> None:
    """Verify backup contains valid JSON matching previous state."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with complex data
    original_todos = [
        Todo(id=1, text="task with unicode: 你好"),
        Todo(id=2, text='task with "quotes"', done=True),
        Todo(id=3, text="task with \\n newline"),
    ]
    storage.save(original_todos)

    # Overwrite with new data
    storage.save([Todo(id=1, text="simple")])

    # Verify backup contains valid JSON matching original
    backup = db.with_suffix(".json.bak")
    backup_content = json.loads(backup.read_text(encoding="utf-8"))

    assert len(backup_content) == 3
    assert backup_content[0]["text"] == "task with unicode: 你好"
    assert backup_content[1]["text"] == 'task with "quotes"'
    assert backup_content[1]["done"] is True
    assert backup_content[2]["text"] == "task with \\n newline"


def test_backup_failure_doesnt_prevent_save(tmp_path) -> None:
    """Verify backup failure doesn't prevent main save operation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="original")])

    # Mock shutil.copy2 to fail for backup but allow save to proceed
    def failing_copy2(*args, **kwargs):
        raise OSError("Simulated backup failure")

    import shutil
    original_copy2 = shutil.copy2

    with patch.object(shutil, "copy2", failing_copy2):
        # Save should still succeed even if backup fails
        storage.save([Todo(id=1, text="modified")])

    # Restore original
    shutil.copy2 = original_copy2

    # Verify main file was updated
    main_content = json.loads(db.read_text(encoding="utf-8"))
    assert main_content[0]["text"] == "modified"


def test_no_backup_flag_disables_backup(tmp_path) -> None:
    """Verify --no-backup flag (backup_enabled=False) prevents backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_enabled=False)

    # Create initial file
    storage.save([Todo(id=1, text="original")])

    # Overwrite with new data
    storage.save([Todo(id=1, text="modified")])

    # Verify NO backup was created
    backup = db.with_suffix(".json.bak")
    assert not backup.exists(), "No backup should be created when backup_enabled=False"


def test_backup_with_different_db_name(tmp_path) -> None:
    """Verify backup works correctly with different database filenames."""
    # Test with .db extension
    db = tmp_path / "custom.db"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="original")])
    storage.save([Todo(id=1, text="modified")])

    backup = db.with_suffix(".db.bak")
    assert backup.exists()
    backup_content = json.loads(backup.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "original"


def test_backup_rotation_with_custom_max(tmp_path) -> None:
    """Verify backup rotation respects custom max_backups setting."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=5)

    # Create more saves than max_backups
    for i in range(7):
        todos = [Todo(id=1, text=f"version-{i}")]
        storage.save(todos)

    # Should have exactly max_backups (5) backups
    parent_dir = tmp_path
    bak_files = sorted(parent_dir.glob("todo.json.bak*"))
    assert len(bak_files) == 5, f"Expected 5 backups with max_backups=5, got {len(bak_files)}"
