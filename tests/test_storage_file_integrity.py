"""Test to verify storage.py file integrity (Issue #589).

This test ensures that:
1. The FileStorage class is complete
2. All required methods exist (_load, _save, _secure_all_parent_directories)
3. The file has no syntax errors
4. The file is properly truncated with no incomplete code blocks
"""

import ast
import sys
from pathlib import Path

import pytest


def test_storage_file_has_no_syntax_errors():
    """Verify that storage.py has no syntax errors."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    # Try to parse the file as valid Python
    with open(storage_path, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"storage.py has syntax error at line {e.lineno}: {e.msg}")


def test_filestorage_class_is_complete():
    """Verify that FileStorage class has all required methods."""
    from flywheel.storage import FileStorage

    # Check that all required methods exist
    required_methods = ["_load", "_save", "_secure_all_parent_directories"]

    for method_name in required_methods:
        assert hasattr(
            FileStorage, method_name
        ), f"FileStorage missing required method: {method_name}"

    # Verify methods are callable
    for method_name in required_methods:
        method = getattr(FileStorage, method_name)
        assert callable(method), f"FileStorage.{method_name} is not callable"


def test_storage_file_is_properly_terminated():
    """Verify that storage.py ends properly with the Storage alias."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # File should end with Storage alias (not empty or truncated code)
    last_non_empty = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            last_non_empty = lines[i].strip()
            break

    assert (
        last_non_empty == "Storage = FileStorage"
    ), f"File should end with 'Storage = FileStorage', but ends with: {last_non_empty}"


def test_no_unclosed_if_blocks():
    """Verify there are no unclosed if statements in the file."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, "r", encoding="utf-8") as f:
        source = f.read()

    # Parse the AST - this will fail if there are syntax errors like unclosed blocks
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"storage.py has unclosed code block at line {e.lineno}: {e.msg}")

    # If we get here, the AST parsed successfully, meaning no unclosed blocks
    assert tree is not None
