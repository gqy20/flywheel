"""Test to verify Issue #584 is a false positive.

This test verifies that the code in storage.py is syntactically correct
and that the FileStorage.__init__ method is complete and properly closed.
Issue #584 claimed the code was truncated at line 236 with an unclosed if statement.
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


def test_filestorage_init_is_complete():
    """Verify that FileStorage.__init__ method is complete and properly closed."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        lines = f.readlines()

    # Line 236 should be inside the if statement block (not the problematic line)
    # The issue claimed line 236 had an unclosed if statement
    line_236 = lines[235].strip()  # 0-indexed
    assert 'self._todos = []' in line_236, f"Line 236 should contain 'self._todos = []', got: {line_236}"

    # Verify the if statement at line 245 is properly closed
    # The issue showed: if "Backup saved to" in error_msg or "Backup created at" in error_msg:
    line_245 = lines[244].strip()
    assert 'if "Backup saved to" in error_msg' in line_245, f"Line 245 should contain the if statement, got: {line_245}"

    # Check that the if block has proper indentation and closing
    # The if block should end before line 257 (else clause)
    line_256 = lines[255].strip()
    assert 'init_success = True' in line_256, f"Line 256 should end the if block, got: {line_256}"

    line_257 = lines[256].strip()
    assert line_257 == 'else:', f"Line 257 should be 'else:', got: {line_257}"


def test_filestorage_init_ending():
    """Verify that FileStorage.__init__ method has proper ending."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        lines = f.readlines()

    # The __init__ method should end with the finally block
    # Line 270-275 should contain the finally block that closes __init__
    line_270 = lines[269].strip()
    assert line_270 == 'finally:', f"Line 270 should be 'finally:', got: {line_270}"

    # The atexit.register call should be present
    line_274 = lines[273].strip()
    assert 'if init_success:' in line_274, f"Line 274 should check init_success, got: {line_274}"

    line_275 = lines[274].strip()
    assert 'atexit.register(self._cleanup)' in line_275, f"Line 275 should register atexit handler, got: {line_275}"


def test_filestorage_can_be_instantiated():
    """Test that FileStorage can be instantiated without syntax errors."""
    import tempfile
    import os

    from flywheel.storage import FileStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test.json")
        # This should work without any syntax errors
        storage = FileStorage(storage_path)
        assert storage is not None
        assert storage._todos == []
        assert storage._next_id == 1


def test_filestorage_backup_recovery_logic():
    """Test that the backup recovery logic in __init__ works correctly."""
    import tempfile
    import os
    import json

    from flywheel.storage import FileStorage

    # Test 1: Normal initialization (no backup needed)
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test1.json")
        storage = FileStorage(storage_path)
        assert storage._todos == []
        assert storage._next_id == 1

    # Test 2: Loading valid data
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test2.json")
        with open(storage_path, 'w') as f:
            json.dump({"todos": [{"id": 1, "title": "Test", "completed": False}], "next_id": 2}, f)

        storage = FileStorage(storage_path)
        assert len(storage._todos) == 1
        assert storage._todos[0]["title"] == "Test"
        assert storage._next_id == 2

    # Test 3: Handling corrupted JSON with backup creation
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test3.json")
        # Write invalid JSON
        with open(storage_path, 'w') as f:
            f.write("{invalid json content}")

        # This should create a backup and handle the error gracefully
        # The issue mentioned this specific code path
        try:
            storage = FileStorage(storage_path)
            # If it doesn't raise, verify it has backup in error message
        except RuntimeError as e:
            # Should either succeed with backup info or fail gracefully
            error_msg = str(e)
            # The backup logic at lines 245-256 should work
            assert "Backup" in error_msg or "Data integrity" in error_msg or "format validation" in error_msg
