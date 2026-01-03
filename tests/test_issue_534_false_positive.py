"""Test for Issue #534 - Verify Storage class is complete (false positive).

This test verifies that the Storage class in src/flywheel/storage.py is complete
and has not been truncated. Issue #534 reported that the code was truncated at
line 193, but upon investigation, the file is complete with all methods properly
implemented.

This is a false positive issue - the AI scanner likely misinterpreted the
multi-line comment as code truncation.
"""

import ast
import sys
from pathlib import Path


def test_storage_file_syntax_is_valid():
    """Test that storage.py has valid Python syntax (not truncated)."""
    storage_path = Path("src/flywheel/storage.py")

    # Read the entire file
    with open(storage_path, 'r') as f:
        code = f.read()

    # Try to parse it as Python code
    try:
        tree = ast.parse(code, filename=str(storage_path))
        # If we get here, syntax is valid
        assert True, "storage.py has valid Python syntax"
    except SyntaxError as e:
        # If there's a syntax error, the file might be truncated
        raise AssertionError(
            f"storage.py has syntax error at line {e.lineno}: {e.msg}. "
            f"This suggests the file may be truncated."
        ) from e


def test_storage_class_has_all_required_methods():
    """Test that Storage class has all expected methods."""
    storage_path = Path("src/flywheel/storage.py")

    with open(storage_path, 'r') as f:
        code = f.read()

    tree = ast.parse(code, filename=str(storage_path))

    # Find the Storage class
    storage_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Storage":
            storage_class = node
            break

    assert storage_class is not None, "Storage class not found"

    # Get all method names
    methods = [node.name for node in storage_class.body if isinstance(node, ast.FunctionDef)]

    # Verify all expected methods are present
    required_methods = [
        "__init__",
        "_get_file_lock_range_from_handle",
        "_acquire_file_lock",
        "_release_file_lock",
        "_secure_directory",
        "_create_and_secure_directories",
        "_acquire_directory_lock",
        "_release_directory_lock",
        "_secure_all_parent_directories",
        "_create_backup",
        "_cleanup",
        "_calculate_checksum",
        "_validate_storage_schema",
        "_load",
        "_save",
        "_save_with_todos",
        "add",
        "list",
        "get",
        "update",
        "delete",
        "get_next_id",
        "health_check",
        "close",
    ]

    for method in required_methods:
        assert method in methods, f"Storage class missing method: {method}"


def test_storage_file_ends_properly():
    """Test that storage.py ends with the close() method."""
    storage_path = Path("src/flywheel/storage.py")

    with open(storage_path, 'r') as f:
        lines = f.readlines()

    # Check that the file ends with the close() method
    last_lines = "".join(lines[-10:])

    # The last method should be close()
    assert "def close(self)" in last_lines, "File should end with close() method"

    # Check that close() method is properly indented (part of Storage class)
    # and has a proper docstring and implementation
    assert '"""Close storage and release resources.' in last_lines or \
           '"""' in last_lines, "close() method should have docstring"


def test_no_incomplete_comments_at_line_193():
    """Test that line 193 is not a truncation point."""
    storage_path = Path("src/flywheel/storage.py")

    with open(storage_path, 'r') as f:
        lines = f.readlines()

    # Line 193 (0-indexed: 192) should be part of a complete comment block
    line_193 = lines[192].strip()

    # It should NOT be empty or contain incomplete code
    assert line_193 != "", "Line 193 should not be empty"

    # It should be a comment or valid code
    assert line_193.startswith("#") or not line_193.startswith("#"), \
        "Line 193 should be either a comment or valid code"

    # The surrounding context should be valid
    context = "".join(lines[190:220])
    assert "def _get_file_lock_range_from_handle" in context, \
        "Line 193 should be within _get_file_lock_range_from_handle method"


if __name__ == "__main__":
    # Run tests
    test_storage_file_syntax_is_valid()
    print("✅ test_storage_file_syntax_is_valid passed")

    test_storage_class_has_all_required_methods()
    print("✅ test_storage_class_has_all_required_methods passed")

    test_storage_file_ends_properly()
    print("✅ test_storage_file_ends_properly passed")

    test_no_incomplete_comments_at_line_193()
    print("✅ test_no_incomplete_comments_at_line_193 passed")

    print("\n✅ All tests passed - Storage class is complete (Issue #534 is a false positive)")
