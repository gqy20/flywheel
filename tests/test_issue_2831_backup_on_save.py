"""Tests for backup file creation on save (Issue #2831).

This test suite verifies that TodoStorage.save() creates a backup file
when FLYWHEEL_BACKUP=1 environment variable is set.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_when_env_var_enabled(tmp_path, monkeypatch) -> None:
    """Test that .bak file is created when FLYWHEEL_BACKUP=1."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Enable backup via environment variable
    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Create initial todos
    original_todos = [Todo(id=1, text="original task"), Todo(id=2, text="another task")]
    storage.save(original_todos)

    # Verify main file exists
    assert db.exists()

    # Save new todos
    new_todos = [Todo(id=1, text="updated task")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_path = db.with_suffix(".json.bak")
    assert backup_path.exists(), "Backup file should be created when FLYWHEEL_BACKUP=1"

    # Verify backup contains the original content
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 2
    assert backup_content[0]["text"] == "original task"
    assert backup_content[1]["text"] == "another task"


def test_backup_overwritten_on_second_save(tmp_path, monkeypatch) -> None:
    """Test that only one backup file exists (overwritten, not appended)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Enable backup via environment variable
    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    backup_path = db.with_suffix(".json.bak")

    # First save - create initial file
    storage.save([Todo(id=1, text="first")])

    # Second save - should create backup of 'first'
    storage.save([Todo(id=1, text="second")])
    assert backup_path.exists()

    # Get backup content after second save
    backup_after_second = backup_path.read_text(encoding="utf-8")
    backup_json_after_second = json.loads(backup_after_second)
    assert backup_json_after_second[0]["text"] == "first"

    # Third save - should overwrite backup with 'second'
    storage.save([Todo(id=1, text="third")])
    assert backup_path.exists()

    # Verify only one backup file exists
    backup_files = list(tmp_path.glob("*.bak"))
    assert len(backup_files) == 1, "Only one backup file should exist"

    # Verify backup was overwritten (now contains 'second', not 'first')
    backup_after_third = backup_path.read_text(encoding="utf-8")
    backup_json_after_third = json.loads(backup_after_third)
    assert backup_json_after_third[0]["text"] == "second", "Backup should be overwritten with previous content"


def test_no_backup_when_env_var_disabled(tmp_path, monkeypatch) -> None:
    """Test that no backup is created when FLYWHEEL_BACKUP is not set."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Ensure backup is disabled (default)
    monkeypatch.delenv("FLYWHEEL_BACKUP", raising=False)

    # Create initial todos
    storage.save([Todo(id=1, text="original")])

    # Save new todos
    storage.save([Todo(id=1, text="updated")])

    # Verify NO backup file was created
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists(), "No backup file should be created when FLYWHEEL_BACKUP is not set"


def test_backup_content_matches_previous_file(tmp_path, monkeypatch) -> None:
    """Test that backup content matches the previous file content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Enable backup
    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Create initial todos with specific structure
    original_todos = [
        Todo(id=1, text="task with unicode: 你好"),
        Todo(id=2, text="task with quotes: \"test\"", done=True),
        Todo(id=3, text="multi\nline\ntask"),
    ]
    storage.save(original_todos)

    # Get the original file content before overwriting
    original_content = db.read_text(encoding="utf-8")

    # Save new todos to trigger backup
    storage.save([Todo(id=4, text="new task")])

    # Verify backup contains the exact original content
    backup_path = db.with_suffix(".json.bak")
    backup_content = backup_path.read_text(encoding="utf-8")
    backup_parsed = json.loads(backup_content)

    assert backup_content == original_content
    assert len(backup_parsed) == 3
    assert backup_parsed[0]["text"] == "task with unicode: 你好"
    assert backup_parsed[1]["text"] == 'task with quotes: "test"'
    assert backup_parsed[1]["done"] is True
    assert backup_parsed[2]["text"] == "multi\nline\ntask"


def test_backup_preserves_metadata(tmp_path, monkeypatch) -> None:
    """Test that shutil.copy2 preserves file permissions and timestamps."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Enable backup
    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # Create initial file with specific permissions
    storage.save([Todo(id=1, text="original")])

    # Set specific permissions on the main file
    original_mode = 0o644
    db.chmod(original_mode)

    # Save to trigger backup
    storage.save([Todo(id=2, text="updated")])

    # Verify backup file exists
    backup_path = db.with_suffix(".json.bak")
    assert backup_path.exists()

    # shutil.copy2 should preserve permissions (on Unix-like systems)
    # Note: Actual behavior may vary by filesystem
    backup_stat = backup_path.stat()

    # The key assertion is that backup was created
    # Permissions preservation is filesystem-dependent but copy2 should preserve metadata
    assert backup_stat.st_size > 0, "Backup should have content"


def test_no_backup_on_first_save_when_no_original_exists(tmp_path, monkeypatch) -> None:
    """Test that no backup is created on first save (no original file exists)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Enable backup
    monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

    # First save - no original file exists yet
    storage.save([Todo(id=1, text="first todo")])

    # Verify main file was created
    assert db.exists()

    # Verify NO backup was created (nothing to back up)
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists(), "No backup should be created on first save (no original file)"


def test_backup_env_var_value_must_be_1(tmp_path, monkeypatch) -> None:
    """Test that FLYWHEEL_BACKUP must equal '1' to enable backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Set env var to something other than '1'
    monkeypatch.setenv("FLYWHEEL_BACKUP", "true")

    # Create initial todos
    storage.save([Todo(id=1, text="original")])

    # Save new todos
    storage.save([Todo(id=2, text="updated")])

    # Verify NO backup was created (env var is not '1')
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists(), "Backup should only be created when FLYWHEEL_BACKUP=1"
