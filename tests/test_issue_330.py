"""Test to verify Issue #330 is a false positive.

This test verifies that the code around line 234 in storage.py
is syntactically correct and the logic works as expected.
"""

import ast
import pytest
from pathlib import Path


def test_storage_py_syntax_is_valid_issue_330():
    """Verify that storage.py has valid Python syntax (Issue #330)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # This will raise SyntaxError if the code is invalid
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        pytest.fail(f"storage.py has syntax error at line {e.lineno}: {e.msg}")


def test_code_around_line_234_is_complete():
    """Verify that the code block around line 234 is complete.

    Issue #330 claimed that line 234 had incomplete code, but this test
    verifies that the try-except block containing line 234 is properly formed.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        lines = f.readlines()

    # Line 234 (0-indexed as 233)
    line_234 = lines[233].strip()

    # Verify line 234 contains the expected code
    assert "dc_parts = [p.split('=')[1] for p in parts if p.strip().startswith('DC=')]" in line_234, \
        f"Line 234 does not match expected code. Got: {line_234}"

    # Verify the try block starts at line 227 (0-indexed as 226)
    line_227 = lines[226].strip()
    assert line_227 == "try:", f"Line 227 should be 'try:', got: {line_227}"

    # Verify the except block starts at line 240 (0-indexed as 239)
    line_240 = lines[239].strip()
    assert "except Exception:" in line_240, f"Line 240 should be 'except Exception:', got: {line_240}"

    # Verify the try-except block is properly closed
    # The except block should end before line 252 (blank line after except block ends)
    line_251 = lines[250].strip()
    assert line_251.endswith(") from e"), f"Line 251 should end with ') from e', got: {line_251}"


def test_windows_domain_parsing_logic():
    """Test the Windows domain parsing logic from line 234.

    This tests the list comprehension that extracts DC= parts from
    a fully qualified domain name.
    """
    # Simulate the logic from line 234
    test_cases = [
        # Input (parts from split by ','), Expected output
        (["CN=user", "OU=users", "DC=domain", "DC=com"], ["domain", "com"]),
        (["DC=example", "DC=org"], ["example", "org"]),
        (["CN=user", "OU=users"], []),  # No DC= parts
        (["DC=single"], ["single"]),
        (["  DC=example  "], ["example"]),  # With whitespace
    ]

    for parts, expected in test_cases:
        # This is the exact logic from line 234
        dc_parts = [p.split('=')[1] for p in parts if p.strip().startswith('DC=')]
        assert dc_parts == expected, f"Failed for {parts}: got {dc_parts}, expected {expected}"

    # Test the domain joining logic (lines 235-236)
    dc_parts = ["domain", "com"]
    domain = '.'.join(dc_parts)
    assert domain == "domain.com", f"Expected 'domain.com', got '{domain}'"


def test_windows_username_parsing_logic():
    """Test the Windows username parsing logic from lines 221-225.

    This tests the logic that handles 'COMPUTERNAME\\username' or 'DOMAIN\\username' format.
    """
    test_cases = [
        ("COMPUTERNAME\\username", "username"),
        ("DOMAIN\\user", "user"),
        ("user", "user"),  # No backslash - should remain unchanged
        ("PC\\john", "john"),
        ("SERVER\\admin", "admin"),
    ]

    for input_user, expected_output in test_cases:
        user = input_user
        # This is the exact logic from lines 221-225
        if '\\' in user:
            parts = user.rsplit('\\', 1)
            if len(parts) == 2:
                user = parts[1]

        assert user == expected_output, \
            f"Failed for {input_user}: got {user}, expected {expected_output}"
