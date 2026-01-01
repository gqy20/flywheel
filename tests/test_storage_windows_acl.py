"""Test to verify Issue #325 is a false positive.

This test verifies that the Windows ACL code in storage.py is complete
and has no truncation issues.
"""

import ast
import pytest
from pathlib import Path


def test_storage_py_syntax_is_valid():
    """Verify that storage.py has valid Python syntax (Issue #325)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # This will raise SyntaxError if the code is invalid
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        pytest.fail(f"storage.py has syntax error at line {e.lineno}: {e.msg}")


def test_secure_directory_windows_complete():
    """Verify that _secure_directory method has complete Windows branch (Issue #325)."""
    storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_file) as f:
        content = f.read()

    # Verify key Windows API calls are present
    required_calls = [
        'LookupAccountName',  # For SID lookup (line 256)
        'SECURITY_DESCRIPTOR',  # For security descriptor initialization (line 288)
        'SetFileSecurity',  # For applying security (line 335)
        'SetSecurityDescriptorOwner',  # For owner setting (line 289)
        'SetSecurityDescriptorDacl',  # For DACL setting (line 311)
        'AddAccessAllowedAce',  # For ACE creation (line 300)
        'DELETE',  # For DELETE permission (Issue #274, line 306)
    ]

    for call in required_calls:
        assert call in content, f"Missing required API call: {call}"

    # Verify the method is complete (no truncation)
    assert 'def _secure_directory' in content
    assert '# Fix Issue #256: Explicitly set DACL protection' in content
    assert 'win32security.SetFileSecurity' in content

    # Ensure no truncated comments like '# Bui' exist
    assert '# Bui' not in content, "Found truncated comment '# Bui' - code may be incomplete"

    # Verify line 234 is not truncated
    lines = content.split('\n')
    line_234 = lines[233] if len(lines) > 233 else ""
    assert '# Fallback: Use local computer for non-domain environments' in line_234 or \
           'except Exception:' in line_234, \
           f"Line 234 appears truncated: {line_234}"


def test_secure_directory_windows_branch_structure():
    """Verify Windows branch has all required components (Issue #325)."""
    storage_file = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_file) as f:
        lines = f.readlines()

    # Find the Windows branch (line 176: "else:  # Windows")
    windows_branch_start = None
    for i, line in enumerate(lines):
        if i >= 175 and 'else:' in line and '# Windows' in line:
            windows_branch_start = i
            break

    assert windows_branch_start is not None, "Could not find Windows branch"

    # Verify the Windows branch extends to at least line 356 (end of exception handling)
    # and contains all required sections
    windows_branch = ''.join(lines[windows_branch_start:min(360, len(lines))])

    # Check for all major sections
    required_sections = [
        'import win32security',
        'import win32con',
        'import win32api',
        '# Get the current user\'s SID',
        'win32security.LookupAccountName',
        '# Create a security descriptor',
        'win32security.SECURITY_DESCRIPTOR',
        '# Create a DACL',
        'win32security.ACL',
        'AddAccessAllowedAce',
        'SetSecurityDescriptorDacl',
        '# Fix Issue #244: Set SACL',
        'SetSecurityDescriptorSacl',
        '# Fix Issue #256: Explicitly set DACL protection',
        'SetSecurityDescriptorControl',
        'win32security.SetFileSecurity',
        'except ImportError',
        'except Exception',
    ]

    for section in required_sections:
        assert section in windows_branch, f"Windows branch missing section: {section}"
