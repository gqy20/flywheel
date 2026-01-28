"""Tests for storage schema validation (Issue #245, #246)."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage


class TestStorageSchemaValidation:
    """Test suite for _validate_storage_schema method."""

    def test_validate_dict_with_metadata(self):
        """Test validation of dict with metadata field."""
        storage = Storage()
        # Valid dict with metadata
        data = {
            "todos": [],
            "next_id": 1,
            "metadata": {"checksum": "abc123"}
        }
        # Should not raise
        storage._validate_storage_schema(data)

    def test_validate_dict_without_metadata(self):
        """Test validation of dict without metadata field."""
        storage = Storage()
        # Valid dict without metadata (backward compatibility)
        data = {
            "todos": [],
            "next_id": 1
        }
        # Should not raise
        storage._validate_storage_schema(data)

    def test_validate_metadata_invalid_type(self):
        """Test validation fails when metadata is not a dict."""
        storage = Storage()
        # Invalid metadata type
        data = {
            "todos": [],
            "next_id": 1,
            "metadata": "invalid"  # Should be dict
        }
        with pytest.raises(RuntimeError, match="metadata.*must be a dict"):
            storage._validate_storage_schema(data)

    def test_validate_checksum_invalid_type(self):
        """Test validation fails when checksum is not a string."""
        storage = Storage()
        # Invalid checksum type
        data = {
            "todos": [],
            "next_id": 1,
            "metadata": {"checksum": 123}  # Should be string
        }
        with pytest.raises(RuntimeError, match="checksum.*must be a string"):
            storage._validate_storage_schema(data)

    def test_validate_todos_invalid_type(self):
        """Test validation fails when todos is not a list."""
        storage = Storage()
        # Invalid todos type
        data = {
            "todos": "invalid",  # Should be list
            "next_id": 1
        }
        with pytest.raises(RuntimeError, match="todos.*must be a list"):
            storage._validate_storage_schema(data)

    def test_validate_next_id_invalid_type(self):
        """Test validation fails when next_id is not an int."""
        storage = Storage()
        # Invalid next_id type
        data = {
            "todos": [],
            "next_id": "invalid"  # Should be int
        }
        with pytest.raises(RuntimeError, match="next_id.*must be an int"):
            storage._validate_storage_schema(data)

    def test_validate_next_id_invalid_value(self):
        """Test validation fails when next_id is less than 1."""
        storage = Storage()
        # Invalid next_id value
        data = {
            "todos": [],
            "next_id": 0  # Should be >= 1
        }
        with pytest.raises(RuntimeError, match="next_id.*must be >= 1"):
            storage._validate_storage_schema(data)

    def test_validate_list_format(self):
        """Test validation of old list format (backward compatibility)."""
        storage = Storage()
        # Old format - just a list
        data = []
        # Should not raise
        storage._validate_storage_schema(data)

    def test_validate_invalid_top_level_type(self):
        """Test validation fails with invalid top-level type."""
        storage = Storage()
        # Invalid top-level type
        data = "invalid"  # Should be dict or list
        with pytest.raises(RuntimeError, match="expected dict or list"):
            storage._validate_storage_schema(data)

    def test_validate_unexpected_keys_warning(self, caplog):
        """Test that unexpected keys generate a warning."""
        import logging
        storage = Storage()
        # Dict with unexpected key
        data = {
            "todos": [],
            "next_id": 1,
            "unexpected_key": "value"
        }
        with caplog.at_level(logging.WARNING):
            storage._validate_storage_schema(data)
        # Should log warning about unexpected key
        assert "Unexpected keys" in caplog.text or "unexpected_key" in caplog.text

    def test_load_and_save_with_metadata(self):
        """Test end-to-end load and save with metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create storage
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add a todo
            from flywheel.todo import Todo
            todo = Todo(id=1, title="Test todo", status="pending")
            storage.add(todo)

            # Verify file was created with metadata
            with storage_path.open('r') as f:
                data = json.load(f)

            assert "metadata" in data
            assert "checksum" in data["metadata"]
            assert "next_id" in data
            assert data["next_id"] >= 1

            # Load the storage again
            storage2 = Storage(str(storage_path))
            loaded_todos = storage2.list()
            assert len(loaded_todos) == 1
            assert loaded_todos[0].id == 1
            assert loaded_todos[0].title == "Test todo"


class TestIssue246VariableTypo:
    """Test suite for Issue #246 - variable name typo check.

    Issue #246 reported a typo where 'd' was used instead of 'data' in
    the _validate_storage_schema method at line 234. This test ensures
    the correct variable name is used and the code works as expected.
    """

    def test_metadata_validation_uses_correct_variable(self):
        """Test that metadata validation uses 'data' variable correctly (Issue #246).

        This test verifies that the _validate_storage_schema method properly
        accesses the 'metadata' field using the correct variable name 'data'
        and not the typo 'd'.
        """
        storage = Storage()

        # Test with metadata present - should access data["metadata"]
        test_data = {
            "todos": [{"id": 1, "title": "Test", "status": "pending"}],
            "next_id": 2,
            "metadata": {"checksum": "test123"}
        }

        # This should work without raising a NameError for undefined variable 'd'
        storage._validate_storage_schema(test_data)

    def test_metadata_validation_with_invalid_type(self):
        """Test that metadata validation properly rejects invalid types (Issue #246).

        This test ensures that when metadata is present but has the wrong type,
        the validation correctly checks data["metadata"] and raises an error.
        """
        storage = Storage()

        # Test with invalid metadata type
        test_data = {
            "todos": [],
            "next_id": 1,
            "metadata": 123  # Invalid: should be dict
        }

        # Should raise RuntimeError about invalid type
        with pytest.raises(RuntimeError, match="'metadata' must be a dict"):
            storage._validate_storage_schema(test_data)

    def test_checksum_validation_uses_correct_variable(self):
        """Test that checksum validation uses 'data' variable correctly (Issue #246).

        This test verifies that when checking the checksum field inside metadata,
        the code correctly accesses data["metadata"]["checksum"].
        """
        storage = Storage()

        # Test with invalid checksum type
        test_data = {
            "todos": [],
            "next_id": 1,
            "metadata": {"checksum": []}  # Invalid: should be string
        }

        # Should raise RuntimeError about invalid checksum type
        with pytest.raises(RuntimeError, match="'metadata.checksum' must be a string"):
            storage._validate_storage_schema(test_data)
