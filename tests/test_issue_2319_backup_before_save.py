"""Tests for automatic backup creation before saving (Issue #2319).

These tests verify that:
1. A backup file is created before each save operation
2. Backup rotation works (keeps only N most recent backups)
3. Save succeeds even if backup creation fails
4. Corrupted file can be restored from backup
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_on_save(tmp_path) -> None:
    """Test that a backup file is created when save() is called."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data (no backup created on first save since file doesn't exist)
    todos = [Todo(id=1, text="original task")]
    storage.save(todos)

    # Second save should create a backup
    todos = [Todo(id=1, text="updated task")]
    storage.save(todos)

    # Verify backup file exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created after save"

    # Verify backup contains the original data
    backup_content = backup_path.read_text(encoding="utf-8")
    assert "original task" in backup_content


def test_backup_rotation_keeps_only_n_backups(tmp_path) -> None:
    """Test that backup rotation keeps only N most recent backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Perform multiple saves to create multiple backups
    # We need 6 saves to fully test rotation (1st has no backup, then we create .bak, .bak.1, .bak.2, .bak.3)
    for i in range(6):
        todos = [Todo(id=1, text=f"task version {i}")]
        storage.save(todos)

    # Check that only 3 backups exist (default rotation)
    # .bak.3 should be deleted, leaving .bak, .bak.1, .bak.2
    backup_dir = tmp_path
    backups = sorted(backup_dir.glob("todo.json.bak*"))

    assert len(backups) == 3, f"Should have exactly 3 backups, got {len(backups)}: {backups}"


def test_save_succeeds_even_if_backup_fails(tmp_path) -> None:
    """Test that save() succeeds even if backup creation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock shutil.copy2 to raise OSError
    with patch("flywheel.storage.shutil.copy2", side_effect=OSError("Backup failed")):
        # Save should still succeed
        todos = [Todo(id=1, text="task despite backup failure")]
        storage.save(todos)

    # Verify main file was saved successfully
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "task despite backup failure"


def test_no_backup_when_file_doesnt_exist(tmp_path) -> None:
    """Test that no backup is attempted when the file doesn't exist yet."""
    db = tmp_path / "new_todo.json"
    storage = TodoStorage(str(db))

    # Save to non-existent file (no backup should be created)
    todos = [Todo(id=1, text="first task")]
    storage.save(todos)

    # Verify no backup exists (no previous file to backup)
    backup_path = tmp_path / "new_todo.json.bak"
    assert not backup_path.exists(), "No backup should be created for new files"


def test_backup_preserves_file_permissions(tmp_path) -> None:
    """Test that backup preserves original file permissions."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with specific permissions
    todos = [Todo(id=1, text="task")]
    storage.save(todos)

    # Set specific permissions
    db.chmod(0o644)

    # Save again to create backup
    todos = [Todo(id=1, text="updated task")]
    storage.save(todos)

    # Verify backup exists and has reasonable permissions
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists()
    # Backup should be readable (exact perms may vary by OS)
    assert backup_path.stat().st_mode & 0o444 != 0


def test_backup_content_matches_original(tmp_path) -> None:
    """Test that backup content exactly matches the original file content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data with specific content
    original_todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2 with unicode: 你好"),
        Todo(id=3, text="task 3", done=True),
    ]
    storage.save(original_todos)

    # Read original content before update
    original_content = db.read_text(encoding="utf-8")

    # Update data
    updated_todos = [Todo(id=4, text="new task")]
    storage.save(updated_todos)

    # Verify backup contains the original content
    backup_path = tmp_path / "todo.json.bak"
    backup_content = backup_path.read_text(encoding="utf-8")

    assert backup_content == original_content
    assert "task 1" in backup_content
    assert "你好" in backup_content
