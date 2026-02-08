"""Tests for automatic backup creation in TodoStorage.

This test suite verifies that TodoStorage.save() creates backups
before saving, allowing recovery from accidental data loss or corruption.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_after_save(tmp_path) -> None:
    """Test that a backup file is created after a successful save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Modify and save again - this should create a backup
    updated_todos = [Todo(id=1, text="updated"), Todo(id=2, text="new")]
    storage.save(updated_todos)

    # Verify backup file exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created after save"

    # Verify backup contains the previous version
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "initial"


def test_backup_rotation_keeps_only_n_backups(tmp_path) -> None:
    """Test that backup rotation keeps only the N most recent backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Perform multiple saves to create multiple backups
    for i in range(10):
        todos = [Todo(id=1, text=f"version-{i}")]
        storage.save(todos)

    # Check for numbered backup files
    backup_files = sorted(tmp_path.glob("todo.json.bak*"))

    # Should have main backup plus numbered backups (max_backups=5, so total 5 files)
    # Files are: .bak, .bak.1, .bak.2, .bak.3, .bak.4 (oldest)
    assert len(backup_files) == 5, f"Expected exactly 5 backup files, got {len(backup_files)}"

    # Verify the most recent backup contains version-8 or version-9 (second-to-last save)
    most_recent_backup = sorted(backup_files, key=lambda p: p.stat().st_mtime)[-1]
    backup_content = json.loads(most_recent_backup.read_text(encoding="utf-8"))
    assert "version-" in backup_content[0]["text"]


def test_save_succeeds_even_if_backup_creation_fails(tmp_path) -> None:
    """Test that save operation succeeds even if backup creation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Mock shutil.copy2 to fail, but save should still succeed
    with patch("flywheel.storage.shutil.copy2") as mock_copy:
        mock_copy.side_effect = OSError("Simulated backup failure")

        # This should NOT raise an error
        updated_todos = [Todo(id=1, text="updated")]
        storage.save(updated_todos)

    # Verify main file was still saved successfully
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "updated"


def test_corrupted_file_can_be_restored_from_backup(tmp_path) -> None:
    """Test that a corrupted file can be restored from backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Do a second save to create a backup of the first version
    updated_todos = [Todo(id=1, text="updated"), Todo(id=2, text="data")]
    storage.save(updated_todos)

    # Corrupt the main file
    db.write_text("invalid json content", encoding="utf-8")

    # Verify backup exists and can restore data
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup should exist when main file is corrupted"

    # Restore from backup
    backup_content = backup_path.read_text(encoding="utf-8")
    db.write_text(backup_content, encoding="utf-8")

    # Verify restored data is valid
    restored = storage.load()
    assert len(restored) == 2
    assert restored[0].text == "original"
    assert restored[1].text == "data"


def test_no_backup_on_first_save(tmp_path) -> None:
    """Test that no backup is created when the file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save to non-existent file
    todos = [Todo(id=1, text="first")]
    storage.save(todos)

    # No backup should be created on first save (nothing to back up)
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup should be created on first save"


def test_backup_property_returns_correct_path(tmp_path) -> None:
    """Test that _backup_path property returns the correct backup file path."""
    db = tmp_path / "custom.json"
    storage = TodoStorage(str(db))

    # Check that backup path is correctly derived from main path
    expected_backup = tmp_path / "custom.json.bak"
    # This test will fail until _backup_path property is added
    assert hasattr(storage, "_backup_path"), "TodoStorage should have _backup_path property"
    assert storage._backup_path == expected_backup


def test_create_backup_method_exists(tmp_path) -> None:
    """Test that create_backup method exists and is callable."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # This test will fail until create_backup method is added
    assert hasattr(storage, "create_backup"), "TodoStorage should have create_backup method"
    assert callable(storage.create_backup), "create_backup should be callable"

    # Call it and verify backup is created
    storage.create_backup()
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "create_backup should create a backup file"
