"""Test for Issue #219: Type-safe next_id handling after validation.

This test ensures that when _validate_storage_schema validates next_id as an integer,
the _load method uses the validated value directly rather than using .get() which
could return an invalid value if validation failed.
"""
import json
import tempfile
from pathlib import Path
import pytest

from flywheel.storage import Storage


def test_load_with_validated_next_id_uses_direct_access():
    """Test that _load uses data['next_id'] after validation, not .get().

    The issue is that after _validate_storage_schema confirms next_id is an int,
    _load should use data['next_id'] directly. Using .get() could return an
    invalid value if validation was bypassed or modified.
    """
    # Create a temporary storage file with valid next_id
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write a valid storage file with next_id as integer
        valid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"},
                {"id": 2, "title": "Task 2", "status": "pending"}
            ],
            "next_id": 3
        }
        storage_path.write_text(json.dumps(valid_data, indent=2))

        # Load the storage
        storage = Storage(str(storage_path))

        # Verify that next_id is loaded correctly
        assert storage.get_next_id() == 3
        assert len(storage.list()) == 2


def test_load_with_invalid_next_id_type_raises_error():
    """Test that loading with non-integer next_id raises RuntimeError.

    This test verifies that _validate_storage_schema properly catches
    invalid next_id types before they can cause issues in _load.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write storage file with next_id as string (invalid type)
        invalid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"}
            ],
            "next_id": "not-an-integer"  # Invalid: should be int
        }
        storage_path.write_text(json.dumps(invalid_data, indent=2))

        # Attempting to load should raise RuntimeError due to schema validation
        with pytest.raises(RuntimeError, match="Invalid schema.*next_id.*must be an int"):
            Storage(str(storage_path))


def test_load_with_zero_next_id_raises_error():
    """Test that loading with next_id=0 raises RuntimeError.

    This test verifies that _validate_storage_schema checks that next_id >= 1.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write storage file with next_id=0 (invalid value)
        invalid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"}
            ],
            "next_id": 0  # Invalid: must be >= 1
        }
        storage_path.write_text(json.dumps(invalid_data, indent=2))

        # Attempting to load should raise RuntimeError
        with pytest.raises(RuntimeError, match="Invalid schema.*next_id.*must be >= 1"):
            Storage(str(storage_path))


def test_load_with_negative_next_id_raises_error():
    """Test that loading with negative next_id raises RuntimeError.

    This test verifies that _validate_storage_schema checks that next_id >= 1.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Write storage file with negative next_id (invalid value)
        invalid_data = {
            "todos": [
                {"id": 1, "title": "Task 1", "status": "pending"}
            ],
            "next_id": -5  # Invalid: must be >= 1
        }
        storage_path.write_text(json.dumps(invalid_data, indent=2))

        # Attempting to load should raise RuntimeError
        with pytest.raises(RuntimeError, match="Invalid schema.*next_id.*must be >= 1"):
            Storage(str(storage_path))
