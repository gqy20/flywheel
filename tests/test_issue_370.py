"""Tests for Issue #370 - File truncation logic to prevent data corruption.

This test ensures defensive file truncation in write operations.
Even though the current tempfile.mkstemp() + os.replace() pattern naturally
handles this, we want explicit truncation for defensive programming.
"""

import json
import os
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_defensive_file_truncation():
    """Test that file write operations include explicit truncation for safety.

    Even though tempfile.mkstemp() creates new empty files, adding explicit
    truncation is a defensive programming practice that ensures data integrity
    even if the implementation changes in the future.

    This test verifies:
    1. Files are properly sized after save operations
    2. No garbage data remains from previous writes
    3. JSON content is always valid

    Related to Issue #370.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with large data
        storage = Storage(str(storage_path))

        # Add many todos to create a large file
        for i in range(50):
            todo = Todo(
                id=i + 1,
                title=f"Todo {i + 1}",
                description="x" * 500,
                status="pending"
            )
            storage.add(todo)

        original_size = storage_path.stat().st_size
        assert original_size > 10000, f"Original file should be large, got {original_size} bytes"

        # Delete most todos to make data much smaller
        for i in range(2, 51):
            storage.delete(i)

        new_size = storage_path.stat().st_size

        # File should be significantly smaller (proves proper handling)
        assert new_size < original_size / 10, \
            f"File should be properly sized: {new_size} < {original_size / 10}"

        # Verify file content is exactly as expected (no garbage)
        with storage_path.open('rb') as f:
            content = f.read()

        # Verify content is valid UTF-8
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError as e:
            raise AssertionError(f"File content is not valid UTF-8: {e}")

        # Verify content is valid JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise AssertionError(f"File content is not valid JSON: {e}")

        # Verify data integrity
        assert len(data["todos"]) == 1, f"Should have 1 todo, got {len(data['todos'])}"
        assert data["todos"][0]["id"] == 1, "Remaining todo should have id=1"

        # Verify file size exactly matches content size (no extra bytes)
        assert new_size == len(content), \
            f"File size {new_size} should match content size {len(content)}"

        # Verify storage can reload without errors
        storage2 = Storage(str(storage_path))
        todos = storage2.list()
        assert len(todos) == 1, f"Storage should load 1 todo, got {len(todos)}"
        assert todos[0].id == 1, "Loaded todo should have id=1"


def test_file_replace_pattern_safety():
    """Test that the temp file + replace pattern prevents data corruption.

    This test validates that using tempfile.mkstemp() + os.replace() provides
    the safety guarantees described in Issue #370.

    Related to Issue #370.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test.json"

        # Simulate the write pattern used in Storage._save()
        # 1. Create temp file
        fd, temp_path = tempfile.mkstemp(
            dir=tmpdir,
            prefix="test.",
            suffix=".tmp"
        )

        try:
            # Write small data to temp file
            small_data = {"todos": [], "next_id": 1, "metadata": {}}
            data_bytes = json.dumps(small_data).encode('utf-8')

            # Write data
            os.write(fd, data_bytes)
            os.fsync(fd)
            os.close(fd)

            # 2. Atomically replace target
            # First create a large target file
            with storage_path.open('w') as f:
                large_data = {
                    "todos": [{"id": i, "data": "x" * 1000} for i in range(100)],
                    "next_id": 101
                }
                json.dump(large_data, f)

            original_size = storage_path.stat().st_size
            assert original_size > len(data_bytes) * 10, "Target should be much larger"

            # Replace with small temp file
            os.replace(temp_path, storage_path)

            # 3. Verify result
            new_size = storage_path.stat().st_size
            assert new_size == len(data_bytes), \
                f"After replace, size should match new data: {new_size} == {len(data_bytes)}"

            # Verify content is correct
            with storage_path.open('r') as f:
                result = json.load(f)

            assert result == small_data, "Data should match what was written to temp file"

        finally:
            # Cleanup
            try:
                os.unlink(temp_path)
            except OSError:
                pass
