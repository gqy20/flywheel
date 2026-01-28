"""Test to verify Issue #350 is a false positive.

This test verifies that the Windows ACL code in storage.py is complete
around line 234 and has no truncation issues.
"""

import ast
import pytest
from pathlib import Path


def test_storage_py_syntax_is_valid():
    """Verify that storage.py has valid Python syntax (Issue #350)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # This will raise SyntaxError if the code is invalid
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        pytest.fail(f"storage.py has syntax error at line {e.lineno}: {e.msg}")


def test_line_234_is_not_truncated():
    """Verify that line 234 in storage.py is not truncated (Issue #350)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        lines = f.readlines()

    # Line 234 (0-indexed as 233)
    if len(lines) <= 233:
        pytest.fail(f"File has fewer than 234 lines (only {len(lines)} lines)")

    line_234 = lines[233].strip()

    # The issue claims line 234 is truncated with:
    # "try: # Try to get the full"
    # But actually line 234 contains a complete comment about building domain

    # Verify line 234 is not the truncated text from the issue
    assert line_234 != "try:", f"Line 234 should not be truncated 'try:'"
    assert not line_234.startswith("# Try to get the full"), \
        f"Line 234 should not contain truncated comment"

    # Verify the actual content on line 234
    # It should be about building domain from DC= parts
    assert "domain" in line_234.lower() or "dc=" in line_234.lower() or "parts" in line_234.lower(), \
        f"Line 234 should be about domain building, got: {line_234}"


def test_windows_sid_lookup_complete():
    """Verify that Windows SID lookup code is complete (Issue #350)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        content = f.read()

    # Verify the complete Windows SID lookup flow exists
    required_components = [
        'win32api.GetUserName()',  # Get username
        'win32api.GetUserNameEx',  # Get fully qualified DN
        'win32security.LookupAccountName',  # Lookup account to get SID
        'win32security.SECURITY_DESCRIPTOR',  # Create security descriptor
        'win32security.ACL',  # Create DACL
        'AddAccessAllowedAce',  # Add access control entry
        'SetSecurityDescriptorDacl',  # Set DACL
        'SetSecurityDescriptorSacl',  # Set SACL
        'win32security.SetFileSecurity',  # Apply security
    ]

    missing = []
    for component in required_components:
        if component not in content:
            missing.append(component)

    assert len(missing) == 0, \
        f"Missing required Windows security components: {', '.join(missing)}"


def test_no_truncated_comments():
    """Verify there are no obviously truncated comments (Issue #350)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        lines = f.readlines()

    truncated_patterns = [
        '# Try to get the',
        '# Get the',
        '# Bui',
        '# Lo',
        '# Ex',
    ]

    for i, line in enumerate(lines, 1):
        for pattern in truncated_patterns:
            if line.strip() == pattern:
                pytest.fail(f"Found potentially truncated comment at line {i}: {line.strip()}")


def test_method_completion():
    """Verify that _secure_directory method is complete (Issue #350)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        content = f.read()

    # Verify method signature exists
    assert 'def _secure_directory(self, directory: Path)' in content

    # Verify Windows branch exists and is complete
    assert 'else:  # Windows' in content

    # Verify the Windows security setup is complete
    assert 'win32security.SetFileSecurity' in content

    # Verify exception handling exists
    assert 'except ImportError' in content
    assert 'except Exception as e:' in content

    # Verify the method ends with proper error handling
    assert 'Cannot continue without secure directory permissions' in content
