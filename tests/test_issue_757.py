"""Tests for FileStorage.health_check() JSON integrity verification (issue #757)."""

import pytest
import tempfile
import os
import json
from pathlib import Path
from flywheel.storage import FileStorage


def test_health_check_returns_true_for_valid_json(tmp_path):
    """Test that health_check returns True when JSON file is valid (issue #757)."""
    storage_path = tmp_path / "test_valid.json"
    storage = FileStorage(str(storage_path))

    # Create a valid JSON file
    valid_data = [{"id": 1, "title": "Test todo", "status": "pending"}]
    with open(storage_path, 'w') as f:
        json.dump(valid_data, f)

    result = storage.health_check()
    assert result is True, "health_check should return True for valid JSON file"


def test_health_check_returns_false_for_corrupted_json(tmp_path):
    """Test that health_check returns False when JSON file is corrupted (issue #757)."""
    storage_path = tmp_path / "test_corrupted.json"
    storage = FileStorage(str(storage_path))

    # Create a corrupted JSON file
    with open(storage_path, 'w') as f:
        f.write('{"id": 1, "title": "Test", INVALID JSON}')

    result = storage.health_check()
    assert result is False, "health_check should return False for corrupted JSON file"


def test_health_check_returns_false_for_empty_file(tmp_path):
    """Test that health_check returns False when file is empty (issue #757)."""
    storage_path = tmp_path / "test_empty.json"
    storage = FileStorage(str(storage_path))

    # Create an empty file
    storage_path.touch()

    result = storage.health_check()
    assert result is False, "health_check should return False for empty file"


def test_health_check_returns_true_when_file_does_not_exist(tmp_path):
    """Test that health_check returns True when file doesn't exist yet (issue #757)."""
    storage_path = tmp_path / "test_nonexistent.json"
    storage = FileStorage(str(storage_path))

    # File doesn't exist - this is OK for a new storage
    result = storage.health_check()
    assert result is True, "health_check should return True when file doesn't exist yet"


def test_health_check_returns_false_for_invalid_json_structure(tmp_path):
    """Test that health_check returns False when JSON has invalid structure (issue #757)."""
    storage_path = tmp_path / "test_invalid_structure.json"
    storage = FileStorage(str(storage_path))

    # Create a valid JSON but with invalid structure (not a list)
    invalid_structure = {"id": 1, "title": "Not a list"}
    with open(storage_path, 'w') as f:
        json.dump(invalid_structure, f)

    result = storage.health_check()
    assert result is False, "health_check should return False for invalid JSON structure"


def test_health_check_returns_false_for_truncated_json(tmp_path):
    """Test that health_check returns False when JSON is truncated (issue #757)."""
    storage_path = tmp_path / "test_truncated.json"
    storage = FileStorage(str(storage_path))

    # Create a truncated JSON file
    with open(storage_path, 'w') as f:
        f.write('[{"id": 1, "title": "Test"')

    result = storage.health_check()
    assert result is False, "health_check should return False for truncated JSON"
