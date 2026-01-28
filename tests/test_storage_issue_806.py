"""Test for Issue #806 - Verify storage.py has no truncated code.

This test verifies that the storage.py file is complete and has no syntax errors,
particularly checking around line 318 where the issue reported truncated code.
"""

import ast
from pathlib import Path


def test_storage_py_is_complete():
    """Test that storage.py is complete and has no truncated code at line 318."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    assert storage_path.exists(), "storage.py file not found"

    source_code = storage_path.read_text()
    lines = source_code.split('\n')

    # Verify file has sufficient lines (should be much more than 318)
    assert len(lines) > 1000, f"storage.py appears truncated (only {len(lines)} lines)"

    # Check line 318 specifically - should NOT contain just "de"
    if len(lines) >= 318:
        line_318 = lines[317]  # 0-indexed
        assert line_318.strip() != "de", f"Line 318 contains truncated code: '{line_318}'"

        # Line 318 should be complete and valid
        # In the current version, it should contain part of the health_check docstring
        assert len(line_318) > 10 or line_318.strip() == "", \
            f"Line 318 appears incomplete: '{line_318}'"

    # Verify the file can be parsed as valid Python
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(f"storage.py has syntax error at line {e.lineno}: {e.msg}")


def test_storage_methods_are_complete():
    """Test that all abstract methods in storage.py are complete."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    source_code = storage_path.read_text()

    # Parse the source code
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(f"Cannot parse storage.py: {e}")

    # Find all function definitions
    class MethodVisitor(ast.NodeVisitor):
        def __init__(self):
            self.methods = []
            self.incomplete_methods = []

        def visit_FunctionDef(self, node):
            # Check if method has a body (not just 'pass' or truncated)
            if node.body:
                # A complete method should have at least 'pass' or actual code
                # Check if it's not truncated (last line shouldn't be incomplete)
                self.methods.append(node.name)
            self.generic_visit(node)

    visitor = MethodVisitor()
    visitor.visit(tree)

    # Verify we found methods
    assert len(visitor.methods) > 0, "No methods found in storage.py"

    # Key methods that should exist and be complete
    required_methods = [
        '__init__',
        'add',
        'get',
        'list',
        'update',
        'delete',
        'add_batch',
        'delete_batch',
        'update_batch',
        'health_check'
    ]

    for method in required_methods:
        assert method in visitor.methods, f"Required method '{method}' not found in storage.py"


def test_can_import_storage_module():
    """Test that storage module can be imported successfully."""
    try:
        from flywheel.storage import AbstractStorage, FileStorage
        assert AbstractStorage is not None
        assert FileStorage is not None
    except ImportError as e:
        raise AssertionError(f"Failed to import storage module: {e}")
    except SyntaxError as e:
        raise AssertionError(f"storage.py has syntax error preventing import: {e}")
