"""Tests for backup file creation feature (Issue #2831).

This test suite verifies that TodoStorage.save() optionally creates a backup
file (.todo.json.bak) before overwriting existing data, enabling recovery
from accidental data corruption.
"""

from __future__ import annotations

import json
import os

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_when_env_var_enabled(tmp_path, monkeypatch) -> None:
    """Test that .bak file is created when FLYWHEEL_BACKUP=1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Enable backup feature via environment variable
    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Create initial data
    initial_todos = [Todo(id=1, text="initial task")]
    storage.save(initial_todos)

    # Verify main file was created
    assert db.exists()
    initial_content = db.read_text(encoding="utf-8")

    # Save modified data
    modified_todos = [Todo(id=1, text="modified task"), Todo(id=2, text="new task")]
    storage.save(modified_todos)

    # Verify .bak file was created with original content
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created when FLYWHEEL_BACKUP=1"

    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == initial_content, "Backup should contain the original content"

    # Verify main file has new content
    main_content = db.read_text(encoding="utf-8")
    assert main_content != backup_content, "Main file should have new content"


def test_backup_overwritten_on_second_save(tmp_path, monkeypatch) -> None:
    """Test that only one backup file exists (overwritten, not appended)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # First save
    storage.save([Todo(id=1, text="first")])

    # Second save
    storage.save([Todo(id=1, text="second")])

    # Third save
    storage.save([Todo(id=1, text="third")])

    # Verify only one .bak file exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists()

    # Verify no additional backup files (.bak.1, .bak.2, etc.)
    parent_dir = tmp_path
    backup_files = list(parent_dir.glob("*.bak*"))
    assert len(backup_files) == 1, f"Expected 1 backup file, found {len(backup_files)}: {backup_files}"

    # Verify backup contains "second" content (the state before "third" save)
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "second"


def test_no_backup_when_env_var_disabled(tmp_path) -> None:
    """Test that no backup is created when FLYWHEEL_BACKUP is not set."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Ensure env var is NOT set
    os.environ.pop("FLYWHEEL_BACKUP", None)

    # Create initial data
    storage.save([Todo(id=1, text="initial")])

    # Save modified data
    storage.save([Todo(id=1, text="modified")])

    # Verify .bak file was NOT created
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup file should be created when FLYWHEEL_BACKUP is not set"


def test_no_backup_when_file_doesnt_exist(tmp_path, monkeypatch) -> None:
    """Test that no backup is created on first save (no existing file)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Ensure no existing file
    assert not db.exists()

    # First save (no existing file to backup)
    storage.save([Todo(id=1, text="first task")])

    # Verify .bak file was NOT created
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup should be created when original file doesn't exist"


def test_backup_preserves_metadata(tmp_path, monkeypatch) -> None:
    """Test that shutil.copy2() preserves file permissions and timestamps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Create initial file with specific permissions
    storage.save([Todo(id=1, text="initial")])
    original_mode = db.stat().st_mode

    # Modify permissions to something specific (0o644 = rw-r--r--)
    db.chmod(0o644)
    original_mode = db.stat().st_mode

    # Save again
    storage.save([Todo(id=1, text="modified")])

    # Verify backup has same permissions as original had
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists()
    backup_mode = backup_path.stat().st_mode
    assert backup_mode == original_mode, "Backup should preserve original file permissions"


def test_backup_content_matches_original(tmp_path, monkeypatch) -> None:
    """Test that backup contains exact previous file content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # First save
    first_todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2", done=True),
        Todo(id=3, text="task with unicode: 你好"),
    ]
    storage.save(first_todos)

    # Read the first version
    first_version = db.read_text(encoding="utf-8")

    # Second save (modified data)
    second_todos = [
        Todo(id=1, text="modified task 1"),
        Todo(id=2, text="modified task 2"),
    ]
    storage.save(second_todos)

    # Verify backup contains exact first version
    backup_path = tmp_path / "todo.json.bak"
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == first_version, "Backup should contain exact previous content"

    # Verify main file contains second version
    main_content = db.read_text(encoding="utf-8")
    assert main_content != backup_content
    parsed_main = json.loads(main_content)
    assert parsed_main[0]["text"] == "modified task 1"
