"""Tests for issue #2831 - backup file creation on save.

Tests FLYWHEEL_BACKUP environment variable functionality that creates
.bak files before overwriting existing .todo.json files.
"""

import json
import stat
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


@pytest.fixture
def temp_storage(tmp_path: Path) -> TodoStorage:
    """Create a TodoStorage with a temporary file path."""
    return TodoStorage(str(tmp_path / ".todo.json"))


@pytest.fixture
def sample_todos() -> list[Todo]:
    """Create sample todos for testing."""
    return [
        Todo(id=1, text="First task", done=False),
        Todo(id=2, text="Second task", done=True),
    ]


@pytest.fixture
def sample_todos_v2() -> list[Todo]:
    """Create modified sample todos for testing backup content."""
    return [
        Todo(id=1, text="First task", done=True),  # Changed status
        Todo(id=2, text="Second task", done=False),  # Changed status
        Todo(id=3, text="Third task", done=False),  # New task
    ]


class TestBackupOnSave:
    """Test backup file creation when FLYWHEEL_BACKUP is enabled."""

    def test_backup_created_when_env_var_enabled(
        self, temp_storage: TodoStorage, sample_todos: list[Todo], monkeypatch
    ) -> None:
        """Test that .bak file is created when FLYWHEEL_BACKUP=1."""
        # Enable backup
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        # Create initial file
        temp_storage.save(sample_todos)

        # Modify and save again (this should create backup)
        modified_todos = [Todo(id=1, text="Modified task", done=False)]
        temp_storage.save(modified_todos)

        # Verify backup file exists
        backup_path = temp_storage.path.with_suffix(".json.bak")
        assert backup_path.exists(), "Backup file should be created when FLYWHEEL_BACKUP=1"

    def test_backup_overwritten_on_subsequent_saves(
        self, temp_storage: TodoStorage, sample_todos: list[Todo], monkeypatch
    ) -> None:
        """Test that only one backup file exists (overwritten, not appended)."""
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        # Create initial file
        temp_storage.save(sample_todos)

        # First save - creates backup
        todos_v2 = [Todo(id=1, text="Version 2", done=False)]
        temp_storage.save(todos_v2)
        backup_path = temp_storage.path.with_suffix(".json.bak")
        assert backup_path.exists()

        # Second save - should overwrite backup
        todos_v3 = [Todo(id=1, text="Version 3", done=False)]
        temp_storage.save(todos_v3)

        # Verify only one backup file exists
        assert backup_path.exists()
        # The backup should have been overwritten (newer timestamp or different content)
        second_backup_content = backup_path.read_text(encoding="utf-8")
        # The backup should contain the v2 data, not v3
        assert "Version 2" in second_backup_content

    def test_no_backup_when_env_var_disabled(
        self, temp_storage: TodoStorage, sample_todos: list[Todo], monkeypatch
    ) -> None:
        """Test that no backup is created when FLYWHEEL_BACKUP is not set."""
        # Disable backup explicitly
        monkeypatch.delenv("FLYWHEEL_BACKUP", raising=False)

        # Create initial file
        temp_storage.save(sample_todos)

        # Save again
        modified_todos = [Todo(id=1, text="Modified task", done=False)]
        temp_storage.save(modified_todos)

        # Verify no backup file exists
        backup_path = temp_storage.path.with_suffix(".json.bak")
        assert not backup_path.exists(), "Backup file should not be created when FLYWHEEL_BACKUP is disabled"

    def test_backup_content_matches_original(
        self, temp_storage: TodoStorage, sample_todos: list[Todo], sample_todos_v2: list[Todo], monkeypatch
    ) -> None:
        """Test that backup file contains the original content before overwrite."""
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        # Save original todos
        temp_storage.save(sample_todos)

        # Read original content
        original_content = temp_storage.path.read_text(encoding="utf-8")

        # Save new todos (triggers backup)
        temp_storage.save(sample_todos_v2)

        # Verify backup content matches original
        backup_path = temp_storage.path.with_suffix(".json.bak")
        backup_content = backup_path.read_text(encoding="utf-8")

        assert backup_content == original_content, "Backup content should match original file content"

    def test_backup_preserves_metadata(
        self, temp_storage: TodoStorage, sample_todos: list[Todo], monkeypatch, tmp_path
    ) -> None:
        """Test that backup preserves file permissions and timestamps."""
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        # Create initial file with specific permissions
        temp_storage.save(sample_todos)

        # Set specific permissions (0o644 - rw-r--r--)
        original_mode = 0o644
        temp_storage.path.chmod(original_mode)

        # Save new todos (triggers backup)
        modified_todos = [Todo(id=1, text="Modified", done=False)]
        temp_storage.save(modified_todos)

        # Verify backup preserves permissions (shutil.copy2 preserves metadata)
        backup_path = temp_storage.path.with_suffix(".json.bak")
        backup_mode = backup_path.stat().st_mode

        # Extract permission bits
        backup_perms = stat.S_IMODE(backup_mode)
        assert backup_perms == original_mode, f"Backup should preserve permissions (expected {oct(original_mode)}, got {oct(backup_perms)})"

    def test_backup_created_after_temp_write(
        self, temp_storage: TodoStorage, sample_todos: list[Todo], monkeypatch
    ) -> None:
        """Test that backup is created after temp file is successfully written."""
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        # Create initial file
        temp_storage.save(sample_todos)

        # Save new content
        modified_todos = [Todo(id=1, text="Modified", done=False)]
        temp_storage.save(modified_todos)

        # Verify new file exists and backup exists
        assert temp_storage.path.exists()
        backup_path = temp_storage.path.with_suffix(".json.bak")
        assert backup_path.exists()

        # Verify backup has original content
        with open(backup_path, encoding="utf-8") as f:
            backup_data = json.load(f)
        assert len(backup_data) == 2
        assert backup_data[0]["text"] == "First task"

    def test_no_backup_when_file_doesnt_exist(
        self, temp_storage: TodoStorage, sample_todos: list[Todo], monkeypatch
    ) -> None:
        """Test that no backup is created when original file doesn't exist."""
        monkeypatch.setenv("FLYWHEEL_BACKUP", "1")

        # Save to non-existent file (first save)
        temp_storage.save(sample_todos)

        # Verify no backup file exists (nothing to backup)
        backup_path = temp_storage.path.with_suffix(".json.bak")
        assert not backup_path.exists(), "No backup should be created when original file doesn't exist"
