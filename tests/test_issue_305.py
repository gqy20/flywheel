"""Tests for Issue #305 - Code truncation at end of file."""

import ast
import pytest
from pathlib import Path


def test_storage_file_syntax_is_valid():
    """Test that storage.py has valid Python syntax (Issue #305)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    # Read the file and try to parse it as valid Python
    with open(storage_path, 'r') as f:
        source = f.read()

    # This will raise SyntaxError if the file is truncated
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"storage.py has syntax error (file may be truncated): {e}")


def test_storage_class_is_complete():
    """Test that Storage class is properly closed (Issue #305)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        source = f.read()

    # Parse the file
    tree = ast.parse(source)

    # Find the Storage class
    storage_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Storage":
            storage_class = node
            break

    assert storage_class is not None, "Storage class not found"

    # Check that the class has the expected methods
    method_names = [m.name for m in storage_class.body if isinstance(m, ast.FunctionDef)]

    # Check for critical methods
    expected_methods = [
        "__init__",
        "_secure_directory",
        "_load",
        "_save",
        "add",
        "list",
        "get",
        "update",
        "delete",
        "close",
    ]

    for method in expected_methods:
        assert method in method_names, f"Storage class missing method: {method}"


def test_secure_directory_method_is_complete():
    """Test that _secure_directory method has complete Windows DACL code (Issue #305)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        source = f.read()

    # Parse the file
    tree = ast.parse(source)

    # Find the Storage class and _secure_directory method
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Storage":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_secure_directory":
                    # Check that the method has a body
                    assert len(item.body) > 1, "_secure_directory method appears to be truncated"

                    # The method should have multiple statements (if/else for Unix/Windows)
                    # If it's truncated, it might only have a few statements
                    # A complete implementation should have substantial logic
                    assert len(item.body) > 10, "_secure_directory method appears incomplete"

                    return

    pytest.fail("_secure_directory method not found in Storage class")


def test_file_ends_properly():
    """Test that the file doesn't end with incomplete code (Issue #305)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        lines = f.readlines()

    # Check that the file doesn't end with an incomplete statement
    # Get the last few non-empty lines
    last_lines = []
    for line in reversed(lines):
        stripped = line.strip()
        if stripped:
            last_lines.append(stripped)
            if len(last_lines) >= 5:
                break

    # Reverse to get correct order
    last_lines = list(reversed(last_lines))

    # Check for common signs of truncation
    # The file should end with a method definition or a proper statement
    # Common incomplete patterns:
    # - Lines ending with "(" (unclosed parenthesis)
    # - Lines ending with "\" (line continuation)
    # - Incomplete strings
    # - Incomplete comments

    for line in last_lines:
        # Check for unclosed parentheses (common truncation sign)
        if line.endswith("("):
            pytest.fail(f"File may be truncated - found unclosed parenthesis in: {line}")

        # Check for line continuation (should not be at end of file)
        if line.endswith("\\"):
            pytest.fail(f"File may be truncated - found line continuation at end: {line}")

    # Check that file ends with a blank line (Python convention)
    # or at least ends with a complete statement
    assert len(lines) > 0, "File is empty"

    # Last line should be empty or a complete statement
    last_line = lines[-1].strip()
    if last_line:
        # If last line is not empty, it should be a complete statement
        # (not ending with : or other incomplete syntax)
        assert not last_line.endswith(":"), f"File may end with incomplete block: {last_line}"
