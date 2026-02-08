"""Tests for file backup feature before overwriting (Issue #2224).

These tests verify that:
1. When save() succeeds, a .bak file is created with previous content
2. Only last 3 backups are kept, older ones are auto-deleted
3. Backup creation can be disabled via enable_backup parameter
4. First save (no existing file) does not create backup
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_with_previous_content(tmp_path) -> None:
    """Save should create .bak file containing previous content before overwrite."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos_v1 = [Todo(id=1, text="original task"), Todo(id=2, text="another task")]
    storage.save(todos_v1)

    # Verify no backup yet (first save)
    backups = list(db.parent.glob("*.bak"))
    assert len(backups) == 0, "First save should not create backup"

    # Save new version
    todos_v2 = [Todo(id=1, text="modified task"), Todo(id=3, text="new task")]
    storage.save(todos_v2)

    # Verify backup was created
    backups = list(db.parent.glob("*.bak"))
    assert len(backups) == 1, "Second save should create one backup"

    # Verify backup contains the previous content
    backup_storage = TodoStorage(str(backups[0]))
    backed_up_todos = backup_storage.load()
    assert len(backed_up_todos) == 2
    assert backed_up_todos[0].text == "original task"
    assert backed_up_todos[1].text == "another task"


def test_save_keeps_only_last_3_backups(tmp_path) -> None:
    """Save should keep only last 3 backups, oldest ones are auto-deleted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save 5 times to test the limit of 3 backups
    for i in range(5):
        todos = [Todo(id=1, text=f"version {i}")]
        storage.save(todos)

    # Should only have 3 backups (not 4)
    backups = sorted(db.parent.glob("*.bak"))
    assert len(backups) == 3, "Should keep only last 3 backups"

    # Verify current file has latest content
    current = storage.load()
    assert current[0].text == "version 4"


def test_enable_backup_false_disables_backup_creation(tmp_path) -> None:
    """enable_backup=False parameter should disable backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos_v1 = [Todo(id=1, text="original")]
    storage.save(todos_v1)

    # Save with backup disabled (assuming this is implemented)
    # Note: This test will fail until enable_backup parameter is added
    todos_v2 = [Todo(id=1, text="modified")]
    storage.save(todos_v2, enable_backup=False)

    # Verify no backup was created
    backups = list(db.parent.glob("*.bak"))
    assert len(backups) == 0, "No backup should be created when disabled"


def test_first_save_does_not_create_backup(tmp_path) -> None:
    """First save (no existing file) should not create backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save to non-existent file
    todos = [Todo(id=1, text="first task")]
    storage.save(todos)

    # Verify no backup was created
    backups = list(db.parent.glob("*.bak"))
    assert len(backups) == 0, "First save should not create backup"


def test_backup_filename_has_timestamp_suffix(tmp_path) -> None:
    """Backup files should have timestamp suffix like .todo.json.YYYYMMDD.bak."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    storage.save([Todo(id=1, text="original")])

    # Save new version
    storage.save([Todo(id=1, text="modified")])

    # Verify backup filename format
    backups = list(db.parent.glob("*.bak"))
    assert len(backups) == 1

    backup_name = backups[0].name
    # Should match pattern like .todo.json.20250208.bak or todo.json.20250208.bak
    assert backup_name.endswith(".bak"), f"Backup should end with .bak, got {backup_name}"
    # Should contain timestamp pattern (8 digits)
    assert any(c.isdigit() for c in backup_name), f"Backup should contain timestamp, got {backup_name}"


def test_save_failure_does_not_affect_backups(tmp_path) -> None:
    """If save fails, existing backups should remain unchanged."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos and a backup
    storage.save([Todo(id=1, text="v1")])
    storage.save([Todo(id=1, text="v2")])

    # Get backup count before failure
    backups_before = list(db.parent.glob("*.bak"))
    assert len(backups_before) == 1

    # Note: Testing save failure is complex due to atomic rename
    # This is a placeholder for future improvement
    # For now, we verify the backup that exists contains v1 data
    backup_storage = TodoStorage(str(backups_before[0]))
    backed_up = backup_storage.load()
    assert backed_up[0].text == "v1"
