"""Test for Issue #1729 - Verify storage.py syntax is correct and complete.

This test verifies that:
1. The storage.py file has no syntax errors
2. The FileStorage and JSONFormatter classes are complete
3. The code at line 254 and line 264 (the MAX_JSON_SIZE check) is properly implemented

Note: Issue #1729 was reported as a false positive by an AI scanner.
The code is actually complete and correct - the scanner only saw a partial
line "(e.g., many f" which is actually part of the full comment
"(e.g., many fields). This prevents log system congestion."
"""

import ast
from pathlib import Path

from flywheel.storage import FileStorage, JSONFormatter


def test_storage_py_syntax():
    """Test that storage.py has no syntax errors (Issue #1729)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    # Try to parse the file as valid Python
    with open(storage_path, 'r') as f:
        code = f.read()

    try:
        ast.parse(code)
    except SyntaxError as e:
        raise AssertionError(
            f"Issue #1729 FAILED: storage.py has syntax error at line {e.lineno}: {e.msg}"
        )


def test_jsonformatter_max_json_size_implementation():
    """Test that JSONFormatter MAX_JSON_SIZE logic is complete (Issue #1729)."""
    formatter = JSONFormatter()

    # Verify MAX_JSON_SIZE exists and is set correctly
    assert hasattr(JSONFormatter, 'MAX_JSON_SIZE'), \
        "Issue #1729: MAX_JSON_SIZE constant missing from JSONFormatter"
    assert JSONFormatter.MAX_JSON_SIZE == 1 * 1024 * 1024, \
        "MAX_JSON_SIZE should be 1MB"

    # Verify the format method exists and can be called
    assert hasattr(formatter, 'format'), \
        "Issue #1729: JSONFormatter.format method missing"


def test_filestorage_class_complete():
    """Test that FileStorage class is complete (Issue #1729)."""
    # Check for essential methods that prove the class is complete
    required_methods = [
        'add', 'update', 'delete', 'get', 'get_all',
        'close', '__enter__', '__exit__', '__del__'
    ]

    for method in required_methods:
        assert hasattr(FileStorage, method), \
            f"Issue #1729: FileStorage missing method: {method}"


def test_line_264_max_json_size_check():
    """Test that line 264 MAX_JSON_SIZE check is properly implemented (Issue #1729).

    The issue reported that line 264 was truncated at "(e.g., many f".
    This test verifies the actual code is complete.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        lines = f.readlines()

    # Check line 264 (0-indexed as 263)
    line_264 = lines[263].strip()

    # The full comment should be present
    assert "(e.g., many fields)" in line_264 or \
           ("many fields" in lines[262].strip() or "many fields" in lines[264].strip()), \
        f"Issue #1729: Line 264 comment appears truncated. Got: {line_264}"

    # Verify the MAX_JSON_SIZE check follows the comment
    # Lines 265-280 should contain the MAX_JSON_SIZE check logic
    code_section = ''.join(lines[264:281])

    assert "if len(json_output) > self.MAX_JSON_SIZE:" in code_section, \
        "Issue #1729: MAX_JSON_SIZE check missing after line 264"

    assert "excess_bytes" in code_section or "log_data['message']" in code_section, \
        "Issue #1729: Message truncation logic missing after MAX_JSON_SIZE check"


def test_storage_file_ends_properly():
    """Test that storage.py file ends properly (Issue #1729)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        lines = f.readlines()

    # File should end with the return statement from _get_global_metrics
    # Check last few lines
    last_lines = ''.join(lines[-5:])

    assert "return _global_io_metrics" in last_lines, \
        f"Issue #1729: File should end with 'return _global_io_metrics'. Got: {last_lines}"

    # Verify no hanging open blocks by checking indentation
    last_line = lines[-1]
    last_indent = len(last_line) - len(last_line.lstrip())
    assert last_indent == 0 or last_line.strip() == "", \
        f"Issue #1729: File should end at module level (indent=0), got indent={last_indent}"


def test_issue_1729_verification():
    """Comprehensive test for Issue #1729 - code is NOT truncated.

    This test proves that the AI scanner's report was a false positive.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        code = f.read()

    # 1. Check file can be parsed as valid Python
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise AssertionError(
            f"Issue #1729 FAILED: File has syntax error at line {e.lineno}"
        )

    # 2. Check that JSONFormatter class is complete
    jsonformatter_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'JSONFormatter':
            jsonformatter_found = True
            # Should have format method
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            assert 'format' in methods, "JSONFormatter should have format method"
            break

    assert jsonformatter_found, "JSONFormatter class not found in storage.py"

    # 3. Check that FileStorage class is complete
    filestorage_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'FileStorage':
            filestorage_found = True
            # Should have __del__ method (which the scanner thought was missing)
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            assert '__del__' in methods, "FileStorage should have __del__ method"
            break

    assert filestorage_found, "FileStorage class not found in storage.py"

    # 4. Verify the code is importable
    from flywheel.storage import FileStorage, JSONFormatter, Storage
    assert Storage is FileStorage, "Storage should be an alias for FileStorage"
