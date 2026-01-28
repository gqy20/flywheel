"""Test to validate issue #355 - Code truncation verification at line 234.

This test verifies that the code in storage.py line 234 is NOT truncated
and contains complete, valid Python code.

Issue #355 claimed that line 234 contained only "#\\" (truncated comment),
but this test will verify the actual content.
"""

import ast
from pathlib import Path


def test_line_234_not_truncated():
    """Test that line 234 in storage.py is not truncated."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    assert storage_path.exists(), "storage.py file not found"

    # Read the file and get line 234 (1-indexed, so index 233)
    lines = storage_path.read_text().splitlines()
    line_234 = lines[233]  # 0-indexed

    # The issue claimed this line was truncated
    # Verify it's not empty or just a truncated comment
    assert line_234.strip(), "Line 234 should not be empty"

    # Verify the file has valid Python syntax
    source_code = storage_path.read_text()
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(f"storage.py has syntax error at line {e.lineno}: {e}")


def test_storage_class_complete():
    """Test that the Storage class definition is complete."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # Parse the source code
    tree = ast.parse(source_code)

    # Find the Storage class
    class_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Storage":
            class_found = True
            # Verify class has methods
            method_names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            assert "add" in method_names, "Storage class should have 'add' method"
            assert "list" in method_names, "Storage class should have 'list' method"
            assert "get" in method_names, "Storage class should have 'get' method"
            assert "update" in method_names, "Storage class should have 'update' method"
            assert "delete" in method_names, "Storage class should have 'delete' method"
            assert "close" in method_names, "Storage class should have 'close' method"
            break

    assert class_found, "Storage class not found in storage.py"


def test_secure_directory_method_complete():
    """Test that the _secure_directory method is complete."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # Parse the source code
    tree = ast.parse(source_code)

    # Find the _secure_directory method
    method_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_secure_directory":
            method_found = True
            # Verify method has a body (not just pass or ellipsis)
            assert len(node.body) > 1, "_secure_directory method should be complete"
            break

    assert method_found, "_secure_directory method not found in Storage class"


def test_file_syntax_valid():
    """Test that storage.py has valid Python syntax."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # This will raise SyntaxError if the file is truncated or has invalid syntax
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(
            f"storage.py has syntax error - file may be truncated. "
            f"Error at line {e.lineno}: {e.msg}"
        )
