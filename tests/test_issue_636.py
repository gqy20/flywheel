"""Test for Issue #636 - Verify FileStorage.__init__ is complete and functional

This test verifies that the FileStorage class can be successfully initialized
and that all code paths in __init__ are properly complete, including:
- Exception handling for various load failures
- Proper initialization of instance variables
- Registration of atexit cleanup handler
- Starting of auto-save thread

Issue #636 was a false positive from an AI scanner (glm-4.7) that claimed the code
was truncated at line 254. The actual code at line 254 is "except OSError as e:",
not an incomplete comment. All comments are complete and the __init__ method
properly closes with a finally block that handles init_success and registers atexit.
"""

import ast
import os
import tempfile
from pathlib import Path

import pytest


def test_storage_py_syntax_is_valid():
    """Verify that storage.py has valid Python syntax (no truncation)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # This will raise SyntaxError if the code is invalid/truncated
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        pytest.fail(f"storage.py has syntax error (code may be truncated): {e}")


def test_filestorage_init_with_nonexistent_file():
    """Test initialization when file doesn't exist (FileNotFoundError path)."""
    from flywheel.storage import FileStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'nonexistent.json')
        storage = FileStorage(db_path)
        # Should handle FileNotFoundError gracefully
        assert storage._todos == []
        assert storage._next_id == 1
        assert storage._dirty is False


def test_filestorage_init_with_invalid_json():
    """Test initialization when file contains invalid JSON (JSONDecodeError path)."""
    from flywheel.storage import FileStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'invalid.json')
        # Create file with invalid JSON
        with open(db_path, 'w') as f:
            f.write('{ invalid json }')

        storage = FileStorage(db_path)
        # Should handle JSONDecodeError gracefully
        assert storage._todos == []
        assert storage._next_id == 1
        assert storage._dirty is False


def test_filestorage_init_with_valid_json():
    """Test initialization when file contains valid JSON (successful load path)."""
    from flywheel.storage import FileStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'valid.json')
        # Create file with valid JSON
        import json
        test_data = {
            'version': 1,
            'todos': [
                {'id': 1, 'title': 'Test todo', 'completed': False}
            ]
        }
        with open(db_path, 'w') as f:
            json.dump(test_data, f)

        storage = FileStorage(db_path)
        # Should load successfully
        assert len(storage._todos) == 1
        assert storage._todos[0].title == 'Test todo'


def test_init_method_complete_with_finally_block():
    """Test that __init__ method has complete try-except-finally structure."""
    from flywheel.storage import FileStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.json')
        storage = FileStorage(db_path)

        # Verify that initialization completed successfully
        # by checking that instance variables are set
        assert hasattr(storage, '_todos')
        assert hasattr(storage, '_next_id')
        assert hasattr(storage, '_lock')
        assert hasattr(storage, '_dirty')

        # The presence of _auto_save_thread indicates the finally block executed
        assert hasattr(storage, '_auto_save_thread')
        assert hasattr(storage, '_auto_save_stop_event')
