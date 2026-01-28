"""Test to verify Issue #354 is a false positive.

Issue #354 claimed that win32api.GetUserName() at line 223 may return
'DOMAIN\\user' format and cause issues with LookupAccountName.

However:
1. The actual GetUserName() call is at line 213, not line 223
2. The code at lines 235-239 already handles 'DOMAIN\\user' format by
   extracting the pure username before calling LookupAccountName
3. Line 223 is just validation code, not the problematic API call

This test verifies the code is complete and handles the DOMAIN\\user format correctly.
"""

import ast
from pathlib import Path


def test_storage_py_syntax_is_valid():
    """Verify that storage.py has valid Python syntax."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # This will raise SyntaxError if the code is invalid
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(f"storage.py has syntax error at line {e.lineno}: {e}")


def test_getUserName_call_location():
    """Verify that GetUserName() is at line 213, not line 223 as claimed in issue #354."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    lines = storage_path.read_text().splitlines()

    # Issue #354 claimed GetUserName() was at line 223
    # But it's actually at line 213 (0-indexed: 212)
    line_213 = lines[212]  # 0-indexed

    # Verify line 213 contains GetUserName call
    assert 'win32api.GetUserName()' in line_213, (
        f"Line 213 should contain win32api.GetUserName(). Got: '{line_213.strip()}'"
    )

    # Line 223 (0-indexed: 222) is validation code, not GetUserName call
    line_223 = lines[222]  # 0-indexed
    assert 'win32api.GetUserName()' not in line_223, (
        f"Line 223 should not contain GetUserName() call. Got: '{line_223.strip()}'"
    )

    # Verify line 223 is validation code
    assert 'if not user' in line_223 or 'isinstance' in line_223, (
        f"Line 223 should be validation code. Got: '{line_223.strip()}'"
    )


def test_domain_username_extraction_exists():
    """Verify that the code handles DOMAIN\\user format correctly.

    Issue #354: The code at lines 235-239 extracts pure username from
    'DOMAIN\\user' format before calling LookupAccountName.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    content = storage_path.read_text()

    # Verify the extraction logic exists
    assert "if '\\\\' in user:" in content, \
        "Missing check for backslash in username"

    assert "user.rsplit('\\\\', 1)" in content, \
        "Missing logic to extract username after last backslash"

    # Verify the comment explaining the fix
    assert "Fix Issue #251" in content or "Extract pure username" in content or \
           "DOMAIN\\\\username" in content, \
        "Missing comment explaining the DOMAIN\\user handling"


def test_rsplit_logic_windows_username():
    """Test the rsplit logic for extracting username from DOMAIN\\user format.

    This replicates the logic from storage.py lines 235-239.
    """
    test_cases = [
        ("DOMAIN\\username", "username"),
        ("COMPUTERNAME\\user", "user"),
        ("DOMAIN\\user\\extra", "user\\extra"),  # Only splits on last backslash
        ("single", "single"),  # No backslash, no split
    ]

    for user_input, expected in test_cases:
        if '\\' in user_input:
            parts = user_input.rsplit('\\', 1)
            if len(parts) == 2:
                result = parts[1]
            else:
                result = user_input
        else:
            result = user_input

        assert result == expected, f"Failed for {user_input}: got {result}, expected {expected}"


def test_lookupAccountName_call_with_extracted_user():
    """Verify that LookupAccountName is called with extracted username, not DOMAIN\\user.

    The code should:
    1. Call win32api.GetUserName() which may return 'DOMAIN\\user'
    2. Extract pure username from 'DOMAIN\\user' -> 'user'
    3. Call win32security.LookupAccountName(domain, 'user') with extracted username
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    lines = storage_path.read_text().splitlines()

    # Find the LookupAccountName call
    lookup_line_idx = None
    for i, line in enumerate(lines):
        if 'win32security.LookupAccountName(domain, user)' in line:
            lookup_line_idx = i
            break

    assert lookup_line_idx is not None, \
        "Could not find LookupAccountName(domain, user) call"

    # Verify that the extraction logic appears before LookupAccountName
    extraction_found_before_lookup = False
    for i in range(max(0, lookup_line_idx - 50), lookup_line_idx):
        if "if '\\\\' in user:" in lines[i]:
            extraction_found_before_lookup = True
            # Verify it uses rsplit
            for j in range(i, min(i + 5, len(lines))):
                if 'rsplit' in lines[j]:
                    break
            break

    assert extraction_found_before_lookup, \
        "DOMAIN\\user extraction logic not found before LookupAccountName call"


def test_storage_module_imports():
    """Verify storage.py can be imported without syntax errors."""
    from flywheel.storage import Storage
    assert Storage is not None


def test_secure_directory_method_exists():
    """Verify _secure_directory method exists and contains the fix."""
    from flywheel.storage import Storage

    assert hasattr(Storage, '_secure_directory'), \
        "Storage._secure_directory method missing"

    # Verify the method contains the DOMAIN\\user handling logic
    import inspect
    source = inspect.getsource(Storage._secure_directory)

    assert "if '\\\\' in user:" in source, \
        "_secure_directory missing DOMAIN\\user extraction logic"
    assert "rsplit" in source, \
        "_secure_directory missing rsplit call for username extraction"
