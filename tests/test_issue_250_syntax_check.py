"""Test to verify Issue #250 is a false positive.

This test verifies that the code in storage.py is syntactically correct
and that _validate_storage_schema method works as expected.
"""

import ast
import pytest
from pathlib import Path


def test_storage_py_syntax_is_valid():
    """Verify that storage.py has valid Python syntax."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # This will raise SyntaxError if the code is invalid
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        pytest.fail(f"storage.py has syntax error: {e}")


def test_validate_storage_schema_with_dict():
    """Test _validate_storage_schema with dict format."""
    from flywheel.storage import Storage
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        storage = Storage(storage_path)

        # Test with valid dict (new format with metadata)
        valid_dict = {
            "todos": [],
            "next_id": 1,
            "metadata": {"checksum": "abc123"}
        }
        # Should not raise
        storage._validate_storage_schema(valid_dict)

        # Test with invalid metadata type
        with pytest.raises(RuntimeError, match="metadata.*must be a dict"):
            storage._validate_storage_schema({
                "todos": [],
                "metadata": "invalid"
            })

        # Test with invalid checksum type
        with pytest.raises(RuntimeError, match="checksum.*must be a string"):
            storage._validate_storage_schema({
                "todos": [],
                "metadata": {"checksum": 123}
            })


def test_validate_storage_schema_with_list():
    """Test _validate_storage_schema with list format (old format)."""
    from flywheel.storage import Storage
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        storage = Storage(storage_path)

        # Test with valid list (old format)
        valid_list = []
        # Should not raise
        storage._validate_storage_schema(valid_list)


def test_validate_storage_schema_with_invalid_type():
    """Test _validate_storage_schema with invalid top-level type."""
    from flywheel.storage import Storage
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        storage = Storage(storage_path)

        # Test with invalid type
        with pytest.raises(RuntimeError, match="expected dict or list"):
            storage._validate_storage_schema("invalid")
        with pytest.raises(RuntimeError, match="expected dict or list"):
            storage._validate_storage_schema(123)
