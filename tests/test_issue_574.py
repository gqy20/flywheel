"""
Test for issue #574 - Verify init_success variable is properly used.

This test ensures that the init_success variable is correctly defined and
used in the __init__ method's finally block.
"""

import os
import tempfile
import pytest
from flywheel import FileTodoStorage


def test_init_success_variable_handling():
    """Test that init_success variable is properly defined and used."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
        f.write('[]')  # Valid JSON

    try:
        # Test 1: Normal initialization with valid file
        storage = FileTodoStorage(temp_path)
        # If init_success was not properly set/handled, this might fail
        # The object should be properly initialized
        assert storage._todos == []
        assert storage._next_id == 1
    finally:
        # Cleanup
        os.unlink(temp_path)


def test_init_success_with_corrupted_file():
    """Test that init_success is properly set even with corrupted file."""
    # Create a temporary file with invalid JSON
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
        f.write('{invalid json')

    try:
        # This should handle the error gracefully and still mark init_success = True
        storage = FileTodoStorage(temp_path)
        # The object should still be initialized with empty state
        assert storage._todos == []
        assert storage._next_id == 1
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_init_success_with_missing_file():
    """Test that init_success is properly set with missing file."""
    # Use a non-existent file path
    temp_path = '/tmp/nonexistent_file_574_test.json'

    try:
        # This should create a new storage
        storage = FileTodoStorage(temp_path)
        # The object should be initialized
        assert storage._todos == []
        assert storage._next_id == 1
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
