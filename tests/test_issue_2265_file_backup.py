"""Regression tests for issue #2265: Add file backup before overwrite.

This test suite verifies that TodoStorage.save() creates backup files
before overwriting the main database file, providing recovery options
in case of data corruption or accidental modifications.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_file_when_enabled(tmp_path) -> None:
    """Issue #2265: Save should create .backup file before overwriting.

    Before fix: No backup file is created
    After fix: .backup file contains previous content before overwrite
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    initial_todos = [Todo(id=1, text="original task")]
    storage.save(initial_todos)

    # Modify and save again - should create backup
    modified_todos = [Todo(id=1, text="modified task")]
    storage.save(modified_todos)

    # Verify backup file was created with original content
    backup_path = tmp_path / "todo.json.backup"
    assert backup_path.exists(), "Backup file should be created"

    # Backup should contain the original data
    storage_from_backup = TodoStorage(str(backup_path))
    backup_todos = storage_from_backup.load()
    assert len(backup_todos) == 1
    assert backup_todos[0].text == "original task"

    # Main file should have modified data
    current_todos = storage.load()
    assert len(current_todos) == 1
    assert current_todos[0].text == "modified task"


def test_save_with_max_backups_1_keeps_only_one_backup(tmp_path) -> None:
    """Issue #2265: With max_backups=1, only one backup should exist.

    Multiple saves should rotate backups, not accumulate them.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    storage.max_backups = 1

    # First save
    storage.save([Todo(id=1, text="version 1")])

    # Second save
    storage.save([Todo(id=1, text="version 2")])

    # Third save
    storage.save([Todo(id=1, text="version 3")])

    # Should only have one backup file with version 2
    backup_path = tmp_path / "todo.json.backup"
    assert backup_path.exists()

    storage_from_backup = TodoStorage(str(backup_path))
    backup_todos = storage_from_backup.load()
    assert backup_todos[0].text == "version 2"

    # Main file should have version 3
    current_todos = storage.load()
    assert current_todos[0].text == "version 3"

    # No additional backup files should exist
    additional_backups = list(tmp_path.glob("todo.json.backup.*"))
    assert len(additional_backups) == 0


def test_backup_failure_does_not_prevent_main_save(tmp_path) -> None:
    """Issue #2265: If backup creation fails, main save should still succeed.

    This ensures backup feature is non-blocking for data persistence.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    storage.enable_backups = True

    # Create initial todos
    storage.save([Todo(id=1, text="initial")])

    # Make backup directory read-only to simulate backup failure
    backup_path = tmp_path / "todo.json.backup"
    backup_path.touch()
    backup_path.chmod(0o000)  # No permissions

    try:
        # This should still succeed despite backup failure
        storage.save([Todo(id=1, text="new version")])
    finally:
        # Restore permissions for cleanup
        backup_path.chmod(0o644)

    # Main file should be updated despite backup failure
    current_todos = storage.load()
    assert len(current_todos) == 1
    assert current_todos[0].text == "new version"


def test_save_disabled_backup_does_not_create_backup_file(tmp_path) -> None:
    """Issue #2265: When enable_backups=False, no backup should be created.

    This allows users to opt-out of backup feature if not needed.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    storage.enable_backups = False

    # Create initial todos
    storage.save([Todo(id=1, text="initial")])

    # Save again
    storage.save([Todo(id=1, text="modified")])

    # No backup file should exist
    backup_path = tmp_path / "todo.json.backup"
    assert not backup_path.exists(), "No backup should be created when disabled"


def test_max_backups_0_disables_backups(tmp_path) -> None:
    """Issue #2265: Setting max_backups=0 should disable backups.

    This provides an alternative way to disable backup feature.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    storage.max_backups = 0

    # Create initial todos
    storage.save([Todo(id=1, text="initial")])

    # Save again
    storage.save([Todo(id=1, text="modified")])

    # No backup file should exist when max_backups is 0
    backup_path = tmp_path / "todo.json.backup"
    assert not backup_path.exists(), "max_backups=0 should disable backups"


def test_save_creates_no_backup_on_first_write(tmp_path) -> None:
    """Issue #2265: First save should not create backup (nothing to backup).

    Backup is only meaningful when there's existing content to preserve.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save to non-existent file
    storage.save([Todo(id=1, text="first todo")])

    # No backup should be created on first write
    backup_path = tmp_path / "todo.json.backup"
    assert not backup_path.exists(), "No backup on first write to new file"


def test_save_with_max_backups_3_keeps_three_backups(tmp_path) -> None:
    """Issue #2265: With max_backups=3, should keep 3 rotating backups.

    Tests backup rotation mechanism with multiple backup slots.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    storage.max_backups = 3

    # Create multiple saves to test rotation
    versions = ["v1", "v2", "v3", "v4", "v5"]
    for version in versions:
        storage.save([Todo(id=1, text=version)])

    # Should have main file with v5
    current_todos = storage.load()
    assert current_todos[0].text == "v5"

    # Should have 3 backups: v2, v3, v4 (v1 was rotated out)
    backup_path = tmp_path / "todo.json.backup"  # Most recent: v4
    backup_1_path = tmp_path / "todo.json.backup.1"  # v3
    backup_2_path = tmp_path / "todo.json.backup.2"  # v2

    assert backup_path.exists()
    assert backup_1_path.exists()
    assert backup_2_path.exists()

    # Verify backup contents
    storage_b0 = TodoStorage(str(backup_path))
    assert storage_b0.load()[0].text == "v4"

    storage_b1 = TodoStorage(str(backup_1_path))
    assert storage_b1.load()[0].text == "v3"

    storage_b2 = TodoStorage(str(backup_2_path))
    assert storage_b2.load()[0].text == "v2"

    # v1 should not exist (rotated out)
    backup_3_path = tmp_path / "todo.json.backup.3"
    assert not backup_3_path.exists()
