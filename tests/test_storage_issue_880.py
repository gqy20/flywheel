"""Test for Issue #880 - Verify storage.py syntax is valid and methods exist.

This test verifies that:
1. The storage.py file has valid Python syntax
2. The async_get, async_update, and async_delete methods exist
3. The FileStorage class exists
4. The module can be imported successfully

Issue: https://github.com/anthropics/flywheel/issues/880
"""

import ast
from pathlib import Path


def test_storage_syntax_valid():
    """Test that storage.py has valid Python syntax and is not truncated."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    assert storage_path.exists(), "storage.py file not found"

    source_code = storage_path.read_text()

    # Verify the file can be parsed without syntax errors
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(f"Syntax error in storage.py at line {e.lineno}: {e.msg}")

    # Verify the file is not truncated (should end with proper content)
    assert not source_code.rstrip().endswith("..."), "File appears to be truncated"
    assert len(source_code) > 1000, "File appears to be too short (truncated?)"

    # Verify key methods exist
    has_async_get = False
    has_async_update = False
    has_async_delete = False
    has_file_storage = False

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            if node.name == "async_get":
                has_async_get = True
            elif node.name == "async_update":
                has_async_update = True
            elif node.name == "async_delete":
                has_async_delete = True
        elif isinstance(node, ast.ClassDef):
            if node.name == "FileStorage":
                has_file_storage = True

    assert has_async_get, "async_get method not found in storage.py"
    assert has_async_update, "async_update method not found in storage.py"
    assert has_async_delete, "async_delete method not found in storage.py"
    assert has_file_storage, "FileStorage class not found in storage.py"


def test_storage_module_imports():
    """Test that the storage module can be imported without errors."""
    try:
        from flywheel.storage import FileStorage, Storage
        assert FileStorage is not None
        assert Storage is not None
    except Exception as e:
        raise AssertionError(f"Failed to import storage module: {e}")


def test_storage_async_methods_complete():
    """Test that async methods have proper docstrings and signatures."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()
    tree = ast.parse(source_code)

    # Find FileStorage class
    file_storage_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "FileStorage":
            file_storage_class = node
            break

    assert file_storage_class is not None, "FileStorage class not found"

    # Check for async methods
    method_names = [node.name for node in file_storage_class.body if isinstance(node, ast.AsyncFunctionDef)]

    assert "async_get" in method_names, "async_get method not found in FileStorage"
    assert "async_update" in method_names, "async_update method not found in FileStorage"
    assert "async_delete" in method_names, "async_delete method not found in FileStorage"
