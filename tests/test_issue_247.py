"""Test for Issue #247: Verify _validate_storage_schema handles metadata correctly.

This test ensures that the _validate_storage_schema method properly validates
the metadata field, specifically checking that:
1. metadata must be a dict when present
2. metadata.checksum must be a string when present
"""
import json
import tempfile
from pathlib import Path
import pytest

from flywheel.storage import Storage


def test_metadata_with_valid_dict_and_string_checksum():
    """Test that valid metadata with dict and string checksum passes validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write storage file with valid metadata
        valid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"}
            ],
            "next_id": 2,
            "metadata": {
                "checksum": "abc123def456"
            }
        }
        storage_path.write_text(json.dumps(valid_data, indent=2))

        # Should load successfully
        storage = Storage(str(storage_path))
        assert storage.get_next_id() == 2
        assert len(storage.list()) == 1


def test_metadata_with_invalid_non_dict_type_raises_error():
    """Test that metadata with non-dict type raises RuntimeError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write storage file with metadata as string (invalid type)
        invalid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"}
            ],
            "next_id": 2,
            "metadata": "not-a-dict"  # Invalid: should be dict
        }
        storage_path.write_text(json.dumps(invalid_data, indent=2))

        # Attempting to load should raise RuntimeError
        with pytest.raises(RuntimeError, match="Invalid schema.*metadata.*must be a dict"):
            Storage(str(storage_path))


def test_metadata_checksum_with_invalid_non_string_type_raises_error():
    """Test that metadata.checksum with non-string type raises RuntimeError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write storage file with checksum as integer (invalid type)
        invalid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"}
            ],
            "next_id": 2,
            "metadata": {
                "checksum": 12345  # Invalid: should be string
            }
        }
        storage_path.write_text(json.dumps(invalid_data, indent=2))

        # Attempting to load should raise RuntimeError
        with pytest.raises(RuntimeError, match="Invalid schema.*checksum.*must be a string"):
            Storage(str(storage_path))


def test_metadata_with_dict_and_no_checksum_passes():
    """Test that metadata dict without checksum field passes validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write storage file with metadata dict but no checksum
        valid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"}
            ],
            "next_id": 2,
            "metadata": {}  # Empty dict is valid
        }
        storage_path.write_text(json.dumps(valid_data, indent=2))

        # Should load successfully
        storage = Storage(str(storage_path))
        assert storage.get_next_id() == 2
        assert len(storage.list()) == 1


def test_metadata_with_checksum_as_list_raises_error():
    """Test that metadata.checksum as list raises RuntimeError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write storage file with checksum as list (invalid type)
        invalid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"}
            ],
            "next_id": 2,
            "metadata": {
                "checksum": ["abc", "123"]  # Invalid: should be string
            }
        }
        storage_path.write_text(json.dumps(invalid_data, indent=2))

        # Attempting to load should raise RuntimeError
        with pytest.raises(RuntimeError, match="Invalid schema.*checksum.*must be a string"):
            Storage(str(storage_path))


def test_storage_without_metadata_loads_successfully():
    """Test that storage without metadata field loads successfully (backward compatibility)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write storage file without metadata (old format)
        valid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"}
            ],
            "next_id": 2
        }
        storage_path.write_text(json.dumps(valid_data, indent=2))

        # Should load successfully
        storage = Storage(str(storage_path))
        assert storage.get_next_id() == 2
        assert len(storage.list()) == 1
