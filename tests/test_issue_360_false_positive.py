"""Test to verify issue #360 is a false positive.

This test verifies that the code in storage.py is complete and not truncated.
The issue report claimed line 229 was truncated, but the code is actually complete.
"""

import ast
import os
from pathlib import Path


def test_storage_file_syntax_valid():
    """Verify that storage.py has no syntax errors."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    assert storage_path.exists(), "storage.py file not found"

    with open(storage_path, 'r') as f:
        code = f.read()

    # Try to parse the file as valid Python
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise AssertionError(f"Syntax error at line {e.lineno}: {e.msg}")


def test_storage_file_complete():
    """Verify that storage.py is not truncated."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        lines = f.readlines()

    # File should have at least 900 lines (current version has 987)
    assert len(lines) >= 900, f"File appears truncated (only {len(lines)} lines)"


def test_line_229_context_complete():
    """Verify that line 229 and its context are complete."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        lines = f.readlines()

    # Line 229 is index 228 (0-based)
    # It should contain the closing parenthesis for RuntimeError
    line_229 = lines[228].strip()

    # Verify line 229 properly closes the RuntimeError
    assert line_229 == ")", f"Line 229 should be ')', got: {line_229}"

    # Verify the context forms a complete RuntimeError
    context = ''.join(lines[222:229])  # Lines 223-229
    assert 'raise RuntimeError(' in context, "Missing RuntimeError raise statement"
    assert 'Cannot set Windows security' in context, "Missing error message"
    assert 'Install pywin32' in context, "Missing install instructions"
    assert context.count('(') == context.count(')'), "Unbalanced parentheses in context"


def test_windows_acl_code_complete():
    """Verify that the Windows ACL code section is complete."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, 'r') as f:
        code = f.read()

    # Verify the file contains the complete Windows security setup
    assert '_secure_directory' in code, "Missing _secure_directory method"
    assert 'win32security.LookupAccountName' in code, "Missing LookupAccountName call"
    assert 'win32security.ACL()' in code, "Missing ACL creation"
    assert 'SetFileSecurity' in code, "Missing SetFileSecurity call"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
