"""Test file backup/rotation before overwrites (Issue #2145)."""

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_first_save_creates_no_backup_when_file_doesnt_exist(tmp_path: Path) -> None:
    """First save should not create backup when file doesn't exist."""
    db_path = tmp_path / "test.json"
    storage = TodoStorage(path=str(db_path), enable_backups=True)

    todos = [Todo(id=1, text="First todo")]
    storage.save(todos)

    # Main file should be created
    assert db_path.exists()
    # Backup should NOT be created (file didn't exist before)
    backup_path = tmp_path / "test.json.bak"
    assert not backup_path.exists()


def test_second_save_creates_bak_with_previous_content(tmp_path: Path) -> None:
    """Second save should create .bak file with previous content."""
    db_path = tmp_path / "test.json"
    storage = TodoStorage(path=str(db_path), enable_backups=True)

    # First save
    todos_v1 = [Todo(id=1, text="Version 1")]
    storage.save(todos_v1)

    # Second save with different content
    todos_v2 = [Todo(id=1, text="Version 2")]
    storage.save(todos_v2)

    # Main file should have new content
    assert db_path.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "Version 2"

    # Backup should have old content
    backup_path = tmp_path / "test.json.bak"
    assert backup_path.exists()
    backup_storage = TodoStorage(path=str(backup_path))
    backup_todos = backup_storage.load()
    assert len(backup_todos) == 1
    assert backup_todos[0].text == "Version 1"


def test_third_save_overwrites_bak_with_second_version(tmp_path: Path) -> None:
    """Multiple saves should keep only one .bak file (rotate)."""
    db_path = tmp_path / "test.json"
    storage = TodoStorage(path=str(db_path), enable_backups=True)

    # First save
    storage.save([Todo(id=1, text="Version 1")])

    # Second save
    storage.save([Todo(id=1, text="Version 2")])

    # Third save
    storage.save([Todo(id=1, text="Version 3")])

    # Main file should have version 3
    loaded = storage.load()
    assert loaded[0].text == "Version 3"

    # Backup should have version 2 (not version 1)
    backup_path = tmp_path / "test.json.bak"
    backup_storage = TodoStorage(path=str(backup_path))
    backup_todos = backup_storage.load()
    assert backup_todos[0].text == "Version 2"


def test_save_succeeds_even_when_backup_creation_fails(tmp_path: Path) -> None:
    """Save should succeed even if backup creation fails."""
    db_path = tmp_path / "test.json"
    storage = TodoStorage(path=str(db_path), enable_backups=True)

    # First save
    storage.save([Todo(id=1, text="Version 1")])

    # Make backup directory read-only to cause backup failure
    backup_path = tmp_path / "test.json.bak"
    # Create a directory with the same name as our backup file
    backup_path.mkdir()

    # Second save should still succeed despite backup failure
    # (it will fail to create backup because a directory exists with that name)
    storage.save([Todo(id=1, text="Version 2")])

    # Main file should still be updated
    loaded = storage.load()
    assert loaded[0].text == "Version 2"


def test_backup_has_same_content_as_original(tmp_path: Path) -> None:
    """Backup should have identical content to original file."""
    db_path = tmp_path / "test.json"
    storage = TodoStorage(path=str(db_path), enable_backups=True)

    # Create todos with all fields
    todos_v1 = [
        Todo(id=1, text="Full todo", done=True),
        Todo(id=2, text="Another", done=False),
    ]
    storage.save(todos_v1)

    # Save new version
    todos_v2 = [Todo(id=1, text="Updated")]
    storage.save(todos_v2)

    # Backup should have exact original content
    backup_storage = TodoStorage(path=str(tmp_path / "test.json.bak"))
    backup_todos = backup_storage.load()
    assert len(backup_todos) == 2
    assert backup_todos[0].id == 1
    assert backup_todos[0].text == "Full todo"
    assert backup_todos[0].done is True
    assert backup_todos[1].id == 2
    assert backup_todos[1].text == "Another"


def test_backups_disabled_by_default(tmp_path: Path) -> None:
    """Backups should be disabled by default (enable_backups=False)."""
    db_path = tmp_path / "test.json"
    storage = TodoStorage(path=str(db_path))  # No enable_backups parameter

    # First save
    storage.save([Todo(id=1, text="Version 1")])

    # Second save
    storage.save([Todo(id=1, text="Version 2")])

    # No backup should be created
    backup_path = tmp_path / "test.json.bak"
    assert not backup_path.exists()


def test_backups_enabled_when_flag_set(tmp_path: Path) -> None:
    """Backups should only be created when enable_backups=True."""
    db_path = tmp_path / "test.json"
    storage = TodoStorage(path=str(db_path), enable_backups=True)

    # First save
    storage.save([Todo(id=1, text="Version 1")])

    # Second save
    storage.save([Todo(id=1, text="Version 2")])

    # Backup should be created
    backup_path = tmp_path / "test.json.bak"
    assert backup_path.exists()
