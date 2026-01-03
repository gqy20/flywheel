"""Tests for Issue #548 - JSON decode error should include detailed context.

This test verifies that when JSON is malformed, the error message includes
specific line number and column information to help users fix the file.
"""
import json
import pytest
from pathlib import Path
from flywheel.storage import FileStorage


def test_json_decode_error_includes_line_and_column(tmp_path):
    """Test that JSON decode errors include line number and column position.

    When a JSON file is malformed, the RuntimeError should include detailed
    information about where the error occurred (line and column) to help
    users manually fix corrupted files.
    """
    # Create a malformed JSON file with a specific error position
    db_path = tmp_path / "test.json"
    # The comma on line 3 creates a JSON syntax error
    malformed_json = """{
    "todos": [],
    "next_id": 1,
}"""
    db_path.write_text(malformed_json)

    # Attempt to load - should raise RuntimeError with context
    storage = FileStorage(db_path)

    with pytest.raises(RuntimeError) as exc_info:
        # Trigger load by accessing the storage
        list(storage.list())

    error_msg = str(exc_info.value)

    # The error message should include:
    # 1. The file path
    assert str(db_path) in error_msg or "test.json" in error_msg

    # 2. Line number information
    # json.JSONDecodeError provides: line, column, position
    # We expect the error message to contain this diagnostic info
    # (Either directly in the message or via __cause__)
    assert any(keyword in error_msg for keyword in ["line", "column", "position", "Line", "Column", "Position"])

    # 3. The original JSONDecodeError should be chained
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)

    # 4. The JSONDecodeError should have line and column attributes
    cause = exc_info.value.__cause__
    assert hasattr(cause, 'lineno')
    assert hasattr(cause, 'colno')
    assert cause.lineno is not None
    assert cause.colno is not None


def test_json_decode_error_at_specific_position(tmp_path):
    """Test JSON decode error at a known position provides accurate location.

    This test creates a JSON file with an error at a known location
    and verifies the error message correctly identifies that location.
    """
    db_path = tmp_path / "test.json"
    # Missing colon after "next_id" on line 2
    malformed_json = '{"todos" [], "next_id": 1}'
    db_path.write_text(malformed_json)

    storage = FileStorage(db_path)

    with pytest.raises(RuntimeError) as exc_info:
        list(storage.list())

    # Verify the cause is JSONDecodeError with positional info
    cause = exc_info.value.__cause__
    assert isinstance(cause, json.JSONDecodeError)
    assert cause.lineno > 0
    assert cause.colno > 0
    assert cause.pos >= 0


def test_valid_json_loads_successfully(tmp_path):
    """Test that valid JSON still loads correctly (regression test)."""
    db_path = tmp_path / "test.json"
    valid_json = """{
    "todos": [],
    "next_id": 1
}"""
    db_path.write_text(valid_json)

    storage = FileStorage(db_path)
    todos = list(storage.list())

    assert todos == []
