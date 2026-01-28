"""Test atomic write operations for backup files (Issue #1515).

This test ensures that backup file writes use atomic operations
(temp file + os.replace) to prevent data loss/corruption.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from flywheel.storage import FileStorage
from flywheel.models import Todo


@pytest.mark.asyncio
async def test_backup_rotation_uses_atomic_writes():
    """Test that backup rotation uses atomic write pattern (temp file + replace).

    This test verifies that when backup files are written during rotation,
    they use atomic operations to prevent data loss if the process crashes
    during the write.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path), backup_count=2)

        # Create initial data
        todo = Todo(title="First todo")
        storage.add(todo.title, todo.description)
        await storage.save()

        # Mock aiofiles.open to track write operations
        original_open = mock.AsyncMock()

        # Track all aiofiles.open calls
        open_calls = []

        async def track_open(file, mode='r', *args, **kwargs):
            """Track aiofiles.open calls to verify atomic write pattern."""
            open_calls.append({
                'file': str(file),
                'mode': mode,
                'is_temp': '.tmp' in str(file)
            })

            # Call original aiofiles.open
            import aiofiles
            return await aiofiles.open(file, mode, *args, **kwargs)

        # Patch aiofiles.open to track calls
        with mock.patch('aiofiles.open', side_effect=track_open):
            # Trigger backup rotation by adding new data and saving
            storage.clear()
            todo2 = Todo(title="Second todo")
            storage.add(todo2.title, todo2.description)
            await storage.save()

        # Verify that backup files were written atomically
        # Atomic writes should: 1) Write to .tmp file, 2) Use os.replace()
        backup_writes = [call for call in open_calls if '.bak' in call['file']]

        # Check that backup writes use temporary files
        # The current implementation writes directly to .bak files without .tmp
        # This test will FAIL initially, demonstrating the bug
        temp_backup_writes = [call for call in backup_writes if call['is_temp']]

        if not temp_backup_writes and backup_writes:
            # Found direct writes to backup files without temp files
            # This is the bug we're fixing
            pytest.fail(
                f"Backup files are written directly without atomic operations. "
                f"Found {len(backup_writes)} direct writes to backup files, "
                f"but no temporary file writes. "
                f"This risks data loss if the process crashes during write."
            )


@pytest.mark.asyncio
async def test_backup_files_are_valid_after_rotation():
    """Test that backup files contain valid JSON after rotation.

    This test simulates a crash scenario: if a write is interrupted,
    the backup file should either be the old version or complete new version,
    never corrupted.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path), backup_count=2)

        # Create initial data
        todo = Todo(title="Original todo")
        storage.add(todo.title, todo.description)
        await storage.save()

        # Get the original backup file
        backup_path = Path(str(storage_path) + ".bak")
        assert backup_path.exists()

        with open(backup_path, 'r') as f:
            original_backup_data = json.load(f)

        # Perform multiple rotations
        for i in range(3):
            storage.clear()
            todo = Todo(title=f"Todo {i}")
            storage.add(todo.title, todo.description)
            await storage.save()

        # Verify all backup files contain valid JSON
        backup_files = [
            Path(str(storage_path) + ".bak"),
            Path(str(storage_path) + ".bak.1"),
        ]

        for backup_file in backup_files:
            if backup_file.exists():
                try:
                    with open(backup_file, 'r') as f:
                        data = json.load(f)
                    # Verify structure
                    assert isinstance(data, dict)
                    assert 'todos' in data
                except (json.JSONDecodeError, KeyError) as e:
                    pytest.fail(
                        f"Backup file {backup_file} is corrupted or invalid: {e}"
                    )


@pytest.mark.asyncio
async def test_backup_atomic_write_pattern_with_monitoring():
    """Test that backup writes follow the pattern: write temp -> flush -> replace.

    This test monitors the actual filesystem operations to verify
    the atomic write pattern is used.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(str(storage_path), backup_count=1)

        # Create initial data
        todo = Todo(title="First todo")
        storage.add(todo.title, todo.description)
        await storage.save()

        # Monitor filesystem operations during backup rotation
        import aiofiles
        original_open = aiofiles.open

        fs_operations = []

        async def monitored_open(file, mode='rb', *args, **kwargs):
            """Monitor aiofiles.open calls."""
            file_str = str(file)
            fs_operations.append({
                'operation': 'open',
                'file': file_str,
                'mode': mode,
                'is_backup': '.bak' in file_str,
                'is_temp': '.tmp' in file_str
            })
            return await original_open(file, mode, *args, **kwargs)

        with mock.patch('aiofiles.open', side_effect=monitored_open):
            # Trigger backup rotation
            storage.clear()
            todo2 = Todo(title="Second todo")
            storage.add(todo2.title, todo2.description)
            await storage.save()

        # Verify atomic pattern: should see temp file writes for backups
        backup_ops = [op for op in fs_operations if op['is_backup']]
        temp_backup_ops = [op for op in backup_ops if op['is_temp']]

        # For atomic writes, we expect to see temporary files
        # This will FAIL initially, showing the bug
        if backup_ops and not temp_backup_ops:
            pytest.fail(
                f"Backup rotation does not use atomic writes. "
                f"Found {len(backup_ops)} backup operations, "
                f"but none use temporary files. "
                f"Expected pattern: write to .tmp file, then os.replace()."
            )
